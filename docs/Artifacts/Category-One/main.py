
# CS 499 Enhancement:
# Refactored application entry point. Domain routes, configuration,
# database operations, models, business services, and error handling
# are separated into dedicated modules for improved maintainability.


from fastapi import FastAPI

from error_handlers import general_exception_handler
from routers.patients import router as patients_router
from routers.injections import router as injections_router
from routers.body_scans import router as body_scans_router
from routers.labs import router as labs_router
from routers.payments import router as payments_router
from routers.inventory import router as inventory_router
from routers.treatments import router as treatments_router

app = FastAPI()

app.add_exception_handler(
    Exception,
    general_exception_handler
)

app.include_router(patients_router)
app.include_router(injections_router)
app.include_router(body_scans_router)
app.include_router(labs_router)
app.include_router(payments_router)
app.include_router(inventory_router)
app.include_router(treatments_router)


@app.get("/")
def root():
    return {"status": "ok"}


@app.head("/")
def root_head():
    return {"status": "ok"}