from dataclasses import dataclass
from typing import Optional

from httpx import AsyncClient


@dataclass
class Attachment:
    filename: str
    content_type: str
    content: bytes


class Mailgun:
    def __init__(self, api_key: str, domain_name: str):
        self.client = AsyncClient()
        self.auth = ("api", api_key)
        self.domain_name = domain_name

    async def send(self, to_address: str, sender_name: str, subject: str,
                   attachment: Optional[Attachment] = None, user_variables: Optional[dict] = None,
                   options: Optional[dict] = None, **kwargs):
        _user_variables = {f"v:{k}": v for k, v in user_variables.items()} if user_variables else {}
        _options = {f"o:{k}": v for k, v in options.items()} if options else {}
        payload = {"from": f"{sender_name} <mailgun@{self.domain_name}>",
                   "to": to_address,
                   "subject": subject,
                   **kwargs,
                   **_user_variables,
                   **_options}
        files = {"attachment": (attachment.filename, attachment.content, attachment.content_type)} \
            if attachment else None
        await self.client.post(f"https://api.mailgun.net/v3/{self.domain_name}/messages", auth=self.auth, files=files,
                               data=payload)
