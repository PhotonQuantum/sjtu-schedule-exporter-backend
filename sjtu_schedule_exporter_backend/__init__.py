import asyncio
import datetime
import os
from collections import defaultdict
from dataclasses import asdict, dataclass

from fastapi import Body, Depends, FastAPI, HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pysjtu import AsyncSession, Client
from pysjtu.exceptions import LoginException, SessionException
from pysjtu.models import ScheduleCourse
from pysjtu.ocr import JCSSRecognizer, Recognizer
from pysjtu.utils import flatten
from .calendar import schedule_to_ics
from .mailgun import Attachment, Mailgun
from .models import Class, LoginFields, LoginResponse, MailSentResponse, Schedule, SessionField, StudentIDResponse, \
    TermStartResponse
from .store import RedisRateLimitStore, RedisSessionStore, User
from .utils import get_lesson_time

SECRET_KEY = os.environ["SECRET_KEY"]
MAIL_DOMAIN = os.environ.get("MAIL_DOMAIN")
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
DEBUG = os.environ.get("DEBUG") == "true"
ocr_module = JCSSRecognizer("https://jcss.lightquantum.me")
store = RedisSessionStore()
rate_limit_store = RedisRateLimitStore()
mail_lock = defaultdict(asyncio.Lock)
if MAIL_DOMAIN or MAILGUN_API_KEY:
    mailgun = Mailgun(MAILGUN_API_KEY, MAIL_DOMAIN)
middlewares = [Middleware(CORSMiddleware, allow_origins=["*"])] if DEBUG else []


async def shutdown():
    await ocr_module.close()


app = FastAPI(on_shutdown=[shutdown], middleware=middlewares)


@dataclass(frozen=True)
class Session:
    key: str
    user: User
    session: AsyncSession


def sjtu_session(auto_save: bool = True):
    async def _func(session_field: SessionField = Body(...)) -> Session:
        if not (user := await store.get(session_field.session)):
            raise HTTPException(403, detail="Invalid session.")
        async with AsyncSession(ocr=Recognizer(), retry=[1]) as _session:
            _session.loads(user.state)
            yield Session(session_field.session, user, _session)
            if auto_save:
                await store.put(User(username=user.username, state=_session.dumps()), session_field.session)

    return _func


@app.exception_handler(SessionException)
async def jaccount_session_exception_handler(request: Request, exc: SessionException):
    return JSONResponse({"detail": str(exc)}, status_code=403)


@app.post("/login", response_model=LoginResponse)
async def login(credential: LoginFields):
    async with AsyncSession(ocr=ocr_module, retry=[1]) as session:
        try:
            await session.login(credential.username, credential.password)
        except LoginException:
            raise HTTPException(status_code=403, detail="Wrong username or password.")
        session_state = session.dumps()
        session_state.pop("password")
        user = User(username=credential.username, state=session_state)
    session_id = await store.put(user)
    return LoginResponse(session=session_id)


@app.post("/student_id", response_model=StudentIDResponse)
async def student_id(session: Session = Depends(sjtu_session())):
    client = Client(session.session)
    return StudentIDResponse(student_id=await client.student_id)


@app.post("/schedule", response_model=Schedule)
async def schedule(year: int, term: int, session: Session = Depends(sjtu_session())):
    def parse_class(_class: ScheduleCourse) -> Class:
        class_dict = asdict(_class)
        class_dict["week"] = flatten(class_dict["week"])
        class_dict["time"] = get_lesson_time(list(class_dict["time"]))
        return Class(**class_dict)

    client = Client(session.session)
    _schedule = await client.schedule(year, term)
    _schedule = [parse_class(_class) for _class in _schedule]
    return Schedule(classes=_schedule)


@app.post("/term_start", response_model=TermStartResponse)
async def term_start(session: Session = Depends(sjtu_session())):
    client = Client(session.session)
    _term_start = await client.term_start_date
    return TermStartResponse(term_start=_term_start)


@app.post("/schedule_ics")
async def schedule_ics(year: int, term: int, term_start_date: datetime.date = None,
                       session: Session = Depends(sjtu_session())):
    client = Client(session.session)
    if term_start_date is None:
        term_start_date = await client.term_start_date
    schedule = await client.schedule(year, term)
    return Response(schedule_to_ics(schedule, term_start_date), media_type="text/calendar")


mail_ics_error_responses = {
    501: {"detail": "This server doesn't have mailing capability."},
    429: {"detail": "You are not allowed to send more than 1 email per minute."}
}


@app.post("/mail_ics", response_model=MailSentResponse, responses=mail_ics_error_responses)
async def mail_ics(year: int, term: int, term_start_date: datetime.date = None,
                   session: Session = Depends(sjtu_session())):
    if MAIL_DOMAIN is None or MAILGUN_API_KEY is None:
        raise HTTPException(status_code=501, detail="This server doesn't have mailing capability.")

    mail_address = session.user.username.lower()
    if not mail_address.endswith("@sjtu.edu.cn"):
        mail_address = f"{mail_address}@sjtu.edu.cn"

    async with mail_lock[mail_address]:
        if await rate_limit_store.is_limit(mail_address):
            raise HTTPException(status_code=429, detail="You are not allowed to send more than 1 email per minute.")

        client = Client(session.session)
        if term_start_date is None:
            term_start_date = await client.term_start_date
        schedule = await client.schedule(year, term)
        ics = schedule_to_ics(schedule, term_start_date)

        term_display = {0: "秋季", 1: "春季", 2: "夏季"}[term]
        await mailgun.send(mail_address, "SJTU Schedule Exporter", f"{year}学年{term_display}学期交大课表",
                           attachment=Attachment("schedule.ics", "text/calendar", ics.encode("utf-8")),
                           template="sjtu_schedule_exporter_ics",
                           user_variables={
                               "year": str(year),
                               "term": term_display
                           })
        await rate_limit_store.limit(mail_address)
        return MailSentResponse(to_address=mail_address)


@app.post("/logout")
async def logout(session: Session = Depends(sjtu_session(auto_save=False))):
    await session.session.logout()
    await store.delete(session.key)


@app.post("/silent_logout")
async def logout(session: Session = Depends(sjtu_session())):
    session.session._cache_store = {}
    await session.session.logout()
