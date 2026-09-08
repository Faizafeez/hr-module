from fastapi import FastAPI, HTTPException, Request, Form
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="My Company HR Module")
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "sqlite:///./hr_module.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class EmployeeDatabase(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    employee_code = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    department = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


class EmployeeCreate(BaseModel):
    employee_code: str
    full_name: str
    email: str
    department: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    database = SessionLocal()
    employees = database.query(EmployeeDatabase).all()
    database.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"employees": employees}
    )


@app.post("/employees")
def create_employee(employee: EmployeeCreate):
    database = SessionLocal()

    existing_employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee.employee_code
    ).first()

    if existing_employee:
        database.close()
        raise HTTPException(
            status_code=400,
            detail="An employee with this code already exists."
        )

    new_employee = EmployeeDatabase(
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department
    )

    database.add(new_employee)
    database.commit()
    database.refresh(new_employee)
    database.close()

    return {
        "message": "Employee saved permanently",
        "employee_id": new_employee.id
    }


@app.get("/employees")
def list_employees():
    database = SessionLocal()
    employees = database.query(EmployeeDatabase).all()

    result = [
        {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "email": employee.email,
            "department": employee.department
        }
        for employee in employees
    ]

    database.close()
    return result

@app.get("/api/employees/{employee_code}")
def get_employee(employee_code: str):
    database = SessionLocal()

    employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee_code
    ).first()

    if not employee:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    result = {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "email": employee.email,
        "department": employee.department
    }

    database.close()
    return result

@app.post("/employees/form")
def create_employee_from_form(
    employee_code: str = Form(),
    full_name: str = Form(),
    email: str = Form(),
    department: str = Form()
):
    database = SessionLocal()

    new_employee = EmployeeDatabase(
        employee_code=employee_code,
        full_name=full_name,
        email=email,
        department=department
    )

    database.add(new_employee)
    database.commit()
    database.close()

    return RedirectResponse(url="/", status_code=303)

@app.get("/employees/{employee_code}", response_class=HTMLResponse)
def employee_profile(employee_code: str, request: Request):
    database = SessionLocal()

    employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee_code
    ).first()

    if not employee:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    database.close()

    return templates.TemplateResponse(
        request=request,
        name="employee_detail.html",
        context={"employee": employee}
    )