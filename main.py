from fastapi import FastAPI, HTTPException, Request, Form
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Date, Time, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date, time, datetime

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

class LeaveRequestDatabase(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True)
    employee_code = Column(String, nullable=False)
    leave_type = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Pending")

class EmployeeDocumentDatabase(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True)
    employee_code = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    document_number = Column(String, nullable=False)
    expiry_date = Column(Date, nullable=False)

class AttendanceLogDatabase(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True)
    employee_code = Column(String, nullable=False)
    attendance_date = Column(Date, nullable=False)
    punch_in = Column(Time, nullable=False)
    punch_out = Column(Time, nullable=False)
    late_minutes = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False)    

class WorkShiftDatabase(Base):
    __tablename__ = "work_shifts"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    crosses_midnight = Column(Boolean, nullable=False, default=False)
    grace_minutes = Column(Integer, nullable=False, default=5)
    monthly_grace_limit = Column(Integer, nullable=False, default=3)

class EmployeeShiftAssignmentDatabase(Base):
    __tablename__ = "employee_shift_assignments"

    id = Column(Integer, primary_key=True)
    employee_code = Column(String, unique=True, nullable=False)
    shift_id = Column(Integer, ForeignKey("work_shifts.id"), nullable=False)

Base.metadata.create_all(bind=engine)

def create_default_shifts():
    database = SessionLocal()

    shifts = [
        {
            "name": "Factory Day Shift",
            "start_time": "7:00 AM",
            "end_time": "4:00 PM",
            "crosses_midnight": False
        },
        {
            "name": "Factory Night Shift",
            "start_time": "6:00 PM",
            "end_time": "3:00 AM",
            "crosses_midnight": True
        },
        {
            "name": "Office Day Shift",
            "start_time": "8:00 AM",
            "end_time": "5:00 PM",
            "crosses_midnight": False
        }
    ]

    for shift in shifts:
        existing_shift = database.query(WorkShiftDatabase).filter(
            WorkShiftDatabase.name == shift["name"]
        ).first()

        if not existing_shift:
            database.add(
                WorkShiftDatabase(
                    name=shift["name"],
                    start_time=shift["start_time"],
                    end_time=shift["end_time"],
                    crosses_midnight=shift["crosses_midnight"],
                    grace_minutes=5,
                    monthly_grace_limit=3
                )
            )

    database.commit()
    database.close()


create_default_shifts()

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

@app.get("/leave-request", response_class=HTMLResponse)
def leave_request_page(request: Request):
    success = request.query_params.get("success") == "1"

    return templates.TemplateResponse(
        request=request,
        name="leave_request.html",
        context={"success": success}
    )


@app.post("/leave-requests")
def submit_leave_request(
    employee_code: str = Form(),
    leave_type: str = Form(),
    start_date: str = Form(),
    end_date: str = Form(),
    reason: str = Form()
):
    database = SessionLocal()

    employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee_code
    ).first()

    if not employee:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Employee code was not found."
        )

    new_request = LeaveRequestDatabase(
        employee_code=employee_code,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status="Pending"
    )

    database.add(new_request)
    database.commit()
    database.close()

    return RedirectResponse(
        url="/leave-request?success=1",
        status_code=303
    )

@app.get("/leave-requests", response_class=HTMLResponse)
def list_leave_requests(request: Request):
    database = SessionLocal()

    leave_requests = database.query(LeaveRequestDatabase).order_by(
        LeaveRequestDatabase.id.desc()
    ).all()

    database.close()

    return templates.TemplateResponse(
        request=request,
        name="leave_requests.html",
        context={"leave_requests": leave_requests}
    )


@app.post("/leave-requests/{request_id}/decision")
def decide_leave_request(
    request_id: int,
    status: str = Form()
):
    if status not in ["Approved", "Rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid leave-request decision."
        )

    database = SessionLocal()

    leave_request = database.query(LeaveRequestDatabase).filter(
        LeaveRequestDatabase.id == request_id
    ).first()

    if not leave_request:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Leave request was not found."
        )

    leave_request.status = status
    database.commit()
    database.close()

    return RedirectResponse(
        url="/leave-requests",
        status_code=303
    )

@app.get("/documents", response_class=HTMLResponse)
def documents_page(request: Request):
    database = SessionLocal()

    documents = database.query(EmployeeDocumentDatabase).order_by(
        EmployeeDocumentDatabase.expiry_date
    ).all()

    today = date.today()

    for document in documents:
        document.days_remaining = (document.expiry_date - today).days

    database.close()

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={"documents": documents}
    )


@app.post("/documents")
def add_document(
    employee_code: str = Form(),
    document_type: str = Form(),
    document_number: str = Form(),
    expiry_date: date = Form()
):
    database = SessionLocal()

    employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee_code
    ).first()

    if not employee:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Employee code was not found."
        )

    document = EmployeeDocumentDatabase(
        employee_code=employee_code,
        document_type=document_type,
        document_number=document_number,
        expiry_date=expiry_date
    )

    database.add(document)
    database.commit()
    database.close()

    return RedirectResponse(url="/documents", status_code=303)

@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(request: Request):
    database = SessionLocal()

    attendance_logs = database.query(AttendanceLogDatabase).order_by(
        AttendanceLogDatabase.attendance_date.desc()
    ).all()

    database.close()

    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={"attendance_logs": attendance_logs}
    )


@app.post("/attendance")
def add_attendance(
    employee_code: str = Form(),
    attendance_date: date = Form(),
    punch_in: time = Form(),
    punch_out: time = Form()
):
    database = SessionLocal()

    employee = database.query(EmployeeDatabase).filter(
        EmployeeDatabase.employee_code == employee_code
    ).first()

    if not employee:
        database.close()
        raise HTTPException(
            status_code=404,
            detail="Employee code was not found."
        )

    assignment = database.query(EmployeeShiftAssignmentDatabase).filter(
        EmployeeShiftAssignmentDatabase.employee_code == employee_code
    ).first()

    if not assignment:
        database.close()
        raise HTTPException(
            status_code=400,
            detail="This employee has no assigned shift."
        )

    shift = database.query(WorkShiftDatabase).filter(
        WorkShiftDatabase.id == assignment.shift_id
    ).first()

    shift_start_time = datetime.strptime(
        shift.start_time,
        "%I:%M %p"
    ).time()

    late_minutes = 0
    status = "Present"

    if punch_in > shift_start_time:
        late_minutes = int(
            (
                datetime.combine(attendance_date, punch_in)
                - datetime.combine(attendance_date, shift_start_time)
            ).total_seconds() / 60
        )

        month_start = attendance_date.replace(day=1)

        if attendance_date.month == 12:
            next_month_start = date(attendance_date.year + 1, 1, 1)
        else:
            next_month_start = date(
                attendance_date.year,
                attendance_date.month + 1,
                1
            )

        grace_uses = database.query(AttendanceLogDatabase).filter(
            AttendanceLogDatabase.employee_code == employee_code,
            AttendanceLogDatabase.attendance_date >= month_start,
            AttendanceLogDatabase.attendance_date < next_month_start,
            AttendanceLogDatabase.status == "Grace Used"
        ).count()

        if (
            late_minutes <= shift.grace_minutes
            and grace_uses < shift.monthly_grace_limit
        ):
            status = "Grace Used"
        else:
            status = "Late"

    attendance_log = AttendanceLogDatabase(
        employee_code=employee_code,
        attendance_date=attendance_date,
        punch_in=punch_in,
        punch_out=punch_out,
        late_minutes=late_minutes,
        status=status
    )

    database.add(attendance_log)
    database.commit()
    database.close()

    return RedirectResponse(url="/attendance", status_code=303)