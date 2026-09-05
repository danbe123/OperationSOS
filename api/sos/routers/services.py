"""What is working: the shared on/off state of power, water, gas, internet and phones."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sos import services
from sos.routers import get_db

router = APIRouter(tags=["services"])


class ServicePatch(BaseModel):
    on: bool


@router.get("/services")
def get_services(conn=Depends(get_db)):
    return services.state(conn)


@router.put("/services/{service}")
def put_service(service: str, body: ServicePatch, conn=Depends(get_db)):
    if service not in services.SERVICES:
        raise HTTPException(status_code=404, detail="Unknown service")
    return services.set_service(conn, service, body.on)
