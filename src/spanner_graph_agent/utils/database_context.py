from pydantic import BaseModel

class JsonField(BaseModel):
  key: str
  type: str