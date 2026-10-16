#!/usr/bin/env python3
import asyncio
import sys
from datetime import date, time, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from sqlalchemy import select

from skillbridge.api.repositories.auth.register import RegisterRepository
from skillbridge.api.repositories.role import RoleRepository
from skillbridge.api.repositories.service import ServiceRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.validators.role import CreateRoleInputValidator
from skillbridge.api.validators.service import CreateServiceInputValidator, ServiceLevel
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.database.db.database import engine, get_session
from skillbridge.database.models.sqlalchemy import Base
from skillbridge.database.models.sqlalchemy.roles import ROLE_ENUM, Role

TUTOR_PROFILES = [
    (
        'Aisha Khan',
        'Computer Science',
        'Python developer who turns programming fundamentals into practical projects.',
        'Hands-on projects and pair programming',
        ['python', 'fastapi', 'sql'],
    ),
    (
        'Lukas Schneider',
        'Software Engineering',
        'Frontend specialist focused on accessible and maintainable web applications.',
        'Visual explanations and live coding',
        ['angular', 'typescript', 'html', 'css'],
    ),
    (
        'Sofia Martinez',
        'Data Science',
        'Data analyst experienced in statistics, visualization, and machine learning.',
        'Dataset-driven exercises',
        ['data science', 'pandas', 'numpy', 'statistics'],
    ),
    (
        'Daniel Weber',
        'Cloud Computing',
        'Cloud engineer helping learners deploy reliable applications.',
        'Architecture diagrams followed by labs',
        ['aws', 'docker', 'kubernetes', 'ci/cd'],
    ),
    (
        'Priya Patel',
        'Artificial Intelligence',
        'Machine-learning tutor with a strong foundation in mathematics.',
        'Theory in small steps with notebook demos',
        ['machine learning', 'python', 'scikit-learn'],
    ),
    (
        'Jonas Mueller',
        'Cyber Security',
        'Security enthusiast teaching defensive development and network fundamentals.',
        'Threat scenarios and guided labs',
        ['cybersecurity', 'linux', 'networking'],
    ),
    (
        'Mei Chen',
        'Information Systems',
        'Database specialist covering relational design and query optimization.',
        'Worked examples and query challenges',
        ['sql', 'mysql', 'database design'],
    ),
    (
        'Noah Williams',
        'Computer Science',
        'Backend developer building APIs with Java and Spring Boot.',
        'Code reviews and incremental exercises',
        ['java', 'spring boot', 'rest api'],
    ),
    (
        'Fatima Zahra',
        'Digital Media',
        'UX designer making user research and interface design approachable.',
        'Collaborative workshops and critique',
        ['ui/ux', 'figma', 'user research'],
    ),
    (
        'Oliver Smith',
        'Applied Mathematics',
        'Mathematics tutor specializing in calculus and linear algebra.',
        'Concept-first problem solving',
        ['calculus', 'linear algebra', 'mathematics'],
    ),
    (
        'Elena Rossi',
        'Business Informatics',
        'Agile practitioner connecting software delivery with business goals.',
        'Case studies and role-playing exercises',
        ['agile', 'scrum', 'project management'],
    ),
    (
        'Samuel Okafor',
        'Mobile Computing',
        'Mobile developer creating cross-platform applications with Flutter.',
        'Build-along mobile projects',
        ['flutter', 'dart', 'mobile development'],
    ),
    (
        'Hannah Fischer',
        'Computer Science',
        'C++ tutor focused on algorithms, memory, and clean code.',
        'Whiteboard reasoning and debugging sessions',
        ['c++', 'algorithms', 'data structures'],
    ),
    (
        'Ravi Mehta',
        'DevOps Engineering',
        'DevOps engineer automating builds, tests, and cloud deployments.',
        'Terminal-based practical labs',
        ['devops', 'terraform', 'github actions', 'linux'],
    ),
    (
        'Emma Johnson',
        'Computer Science',
        'React developer helping students master modern component-based UIs.',
        'Small challenges and live refactoring',
        ['react', 'javascript', 'node'],
    ),
    (
        'Yusuf Demir',
        'Embedded Systems',
        'Embedded engineer teaching electronics, C, and microcontrollers.',
        'Hardware demonstrations and guided experiments',
        ['embedded systems', 'c', 'arduino'],
    ),
    (
        'Marta Kowalska',
        'Data Engineering',
        'Data engineer explaining pipelines, warehouses, and distributed processing.',
        'Pipeline design followed by implementation',
        ['data engineering', 'spark', 'etl', 'python'],
    ),
    (
        'Leo Nguyen',
        'Game Development',
        'Game developer teaching gameplay programming and prototyping.',
        'Rapid prototypes and creative challenges',
        ['unity', 'c#', 'game development'],
    ),
    (
        'Nora Hassan',
        'Computer Science',
        'Software tester passionate about reliable automation and quality practices.',
        'Bug hunts and test-writing workshops',
        ['software testing', 'pytest', 'selenium'],
    ),
    (
        'Benjamin Clark',
        'Blockchain Technology',
        'Distributed-systems tutor covering blockchain concepts and smart contracts.',
        'Concept maps and guided coding',
        ['blockchain', 'solidity', 'distributed systems'],
    ),
]

STUDENT_NAMES = [
    "Mia Becker",
    "Arjun Singh",
    "Laura Garcia",
    "Elias Wagner",
    "Zainab Ali",
    "Theo Martin",
    "Amelia Brown",
    "Omar Ibrahim",
    "Lina Hoffmann",
    "Mateo Silva",
    "Sara Ahmed",
    "Finn Bauer",
    "Isabella Romano",
    "David Kim",
    "Leila Haddad",
    "Maximilian Koch",
    "Chloe Wilson",
    "Aditya Rao",
    "Anna Nowak",
    "Gabriel Costa",
    "Maya Thompson",
    "Karim Mansour",
    "Julia Klein",
    "Nicolas Dubois",
    "Ava Anderson",
    "Ibrahim Kaya",
    "Clara Schmidt",
    "Lucas Pereira",
    "Nadia Rahman",
    "Felix Neumann",
    "Emily Taylor",
    "Vikram Shah",
    "Alina Popescu",
    "Oscar Lindberg",
    "Hana Suzuki",
    "Louis Bernard",
    "Maryam Farooq",
    "Anton Petrov",
    "Grace Lee",
    "Tobias Richter",
]

STUDENT_FIELDS = [
    "Computer Science",
    "International Business",
    "Data Science",
    "Electrical Engineering",
    "Applied Mathematics",
    "Digital Media",
    "Business Informatics",
    "Cyber Security",
    "Mechanical Engineering",
    "Software Engineering",
]

UNIVERSITIES = [
    "Fulda University of Applied Sciences",
    "Technical University of Munich",
    "University of Kassel",
    "Goethe University Frankfurt",
    "RWTH Aachen University",
]

SERVICE_CATALOG = [
    (
        "Python Fundamentals",
        "Learn variables, loops, functions, and clean Python basics.",
        ["python", "programming basics"],
    ),
    (
        "FastAPI Backend Workshop",
        "Build and validate a production-style REST API.",
        ["python", "fastapi", "rest api"],
    ),
    (
        "SQL Query Clinic",
        "Practice joins, aggregates, subqueries, and query optimization.",
        ["sql", "mysql", "database"],
    ),
    (
        "Angular Components Lab",
        "Create reusable components, services, and reactive forms.",
        ["angular", "typescript", "frontend"],
    ),
    (
        "Modern React Essentials",
        "Understand hooks, state, routing, and component design.",
        ["react", "javascript", "frontend"],
    ),
    (
        "Data Analysis with Pandas",
        "Clean, explore, and visualize a realistic dataset.",
        ["pandas", "python", "data science"],
    ),
    (
        "Machine Learning Starter",
        "Train and evaluate your first predictive models.",
        ["machine learning", "scikit-learn", "python"],
    ),
    (
        "Docker from Zero",
        "Containerize an application and run a multi-service stack.",
        ["docker", "devops", "containers"],
    ),
    (
        "AWS Deployment Practice",
        "Deploy a web service and understand core AWS building blocks.",
        ["aws", "cloud", "deployment"],
    ),
    (
        "Kubernetes Foundations",
        "Work with pods, deployments, services, and configuration.",
        ["kubernetes", "devops", "cloud"],
    ),
    (
        "Linux Command Line",
        "Navigate Linux, manage processes, permissions, and shell tools.",
        ["linux", "shell", "devops"],
    ),
    (
        "Git and GitHub Workflow",
        "Practice branching, pull requests, reviews, and conflict resolution.",
        ["git", "github", "collaboration"],
    ),
    (
        "Java and Spring Boot",
        "Develop a layered REST service with Spring Boot.",
        ["java", "spring boot", "backend"],
    ),
    (
        "Algorithms Interview Prep",
        "Solve common algorithm problems and explain tradeoffs.",
        ["algorithms", "data structures", "interview"],
    ),
    (
        "C++ Memory Masterclass",
        "Understand pointers, ownership, RAII, and debugging.",
        ["c++", "memory", "debugging"],
    ),
    (
        "Flutter App Workshop",
        "Build a responsive cross-platform mobile application.",
        ["flutter", "dart", "mobile"],
    ),
    (
        "UI/UX Design Critique",
        "Improve a design using usability and accessibility principles.",
        ["ui/ux", "figma", "accessibility"],
    ),
    (
        "Calculus Problem Session",
        "Work through derivatives, integrals, and applications.",
        ["calculus", "mathematics"],
    ),
    (
        "Linear Algebra Made Visual",
        "Explore vectors, matrices, transformations, and eigenvalues.",
        ["linear algebra", "mathematics"],
    ),
    (
        "Cybersecurity Essentials",
        "Learn threat modeling, secure coding, and common vulnerabilities.",
        ["cybersecurity", "owasp", "security"],
    ),
    (
        "Terraform Infrastructure Lab",
        "Provision repeatable cloud infrastructure as code.",
        ["terraform", "cloud", "devops"],
    ),
    (
        "Automated Testing with Pytest",
        "Write maintainable unit, integration, and API tests.",
        ["pytest", "python", "testing"],
    ),
    (
        "Unity Game Prototype",
        "Create a small playable game while learning Unity fundamentals.",
        ["unity", "c#", "game development"],
    ),
    (
        "Data Pipelines with Spark",
        "Design a batch data pipeline and process large datasets.",
        ["spark", "etl", "data engineering"],
    ),
]

SERVICE_TIMES = [
    time(8, 30),
    time(10, 0),
    time(13, 30),
    time(16, 0),
    time(18, 30),
    time(20, 0),
]


def print_heading(message: str) -> None:
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80 + "\n")


def response_data(response: Any) -> Any:
    """Return repository response data for both dict and model-like responses."""
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


async def reset_database_schema() -> None:
    print_heading("Resetting database schema")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema reset complete.")


async def fetch_role_by_slug(slug: str) -> Role | None:
    async with get_session() as session:
        query = select(Role).where(Role.slug == slug)
        result = await session.execute(query)
        return result.scalars().first()


async def create_role_if_missing(title: ROLE_ENUM, slug: str, description: str) -> Role:
    existing = await fetch_role_by_slug(slug)
    if existing:
        print(f"Role already exists: {slug}")
        return existing

    print(f"Creating role: {slug}")
    validator = CreateRoleInputValidator(
        title=title, slug=slug, description=description
    )
    response = await RoleRepository().create_role(validator)
    return response_data(response)


async def create_user(
    full_name: str,
    email: str,
    password: str,
    role_id: UUID,
    phone: str | None = None,
    academic_program: str | None = None,
    bio: str | None = None,
    teaching_style: str | None = None,
    is_visible: bool | None = True,
    accepting_requests: bool | None = True,
    tags: list[str] | None = None,
    field_of_study: str | None = None,
    enrolled_university: str | None = None,
    graduation_year: int | None = None,
) -> Any:
    print(f"Registering user: {email} ({role_id})")
    register_input = UserRegisterInputValidator(
        full_name=full_name,
        email=email,
        phone=phone,
        password=password,
        confirm_password=password,
        role_id=role_id,
        academic_program=academic_program,
        bio=bio,
        teaching_style=teaching_style,
        is_visible=is_visible,
        accepting_requests=accepting_requests,
        tags=tags,
        field_of_study=field_of_study,
        enrolled_university=enrolled_university,
        graduation_year=graduation_year,
    )
    response = await RegisterRepository().register(register_input)
    return response


async def approve_all_tutor_revisions(admin_user_id: UUID) -> list[dict]:
    print("Fetching pending tutor revisions for admin approval...")
    response = await TutorRepository().get_pending_tutor_revisions(
        admin_user_id, limit=len(TUTOR_PROFILES), offset=0
    )
    pending = response.get("data", [])
    if not pending:
        raise RuntimeError("No pending tutor revisions found.")

    approvals = []
    for revision in pending:
        revision_id = revision["id"]
        print(f"Approving tutor revision: {revision_id}")
        approval = await TutorRepository().approve_tutor_revision(
            UUID(str(revision_id)), admin_user_id
        )
        approvals.append(response_data(approval))

    return approvals


async def create_and_approve_services_for_tutor(
    tutor_id: UUID,
    tutor_index: int,
    admin_user_id: UUID,
    count: int = 6,
) -> list[dict]:
    approved_services = []
    levels = list(ServiceLevel)
    short_tutor_id = str(tutor_id)[:8]

    for service_index in range(count):
        catalog_index = (tutor_index * count + service_index) % len(SERVICE_CATALOG)
        service_name, description, tags = SERVICE_CATALOG[catalog_index]
        session_number = service_index + 1
        session_time = SERVICE_TIMES[(tutor_index + service_index) % len(SERVICE_TIMES)]
        level = levels[(tutor_index + service_index) % len(levels)]

        service_payload = CreateServiceInputValidator(
            tutor_id=tutor_id,
            service_name=service_name,
            description=description,
            date=date.today() + timedelta(days=2 + tutor_index + service_index * 7),
            time=session_time,
            price=15 + ((tutor_index * 7 + service_index * 5) % 46),
            level=level,
            joining_link=(
                f"https://meet.hs-fulda.de/{short_tutor_id}-{session_number}"
            ),
            tags=tags,
        )
        print(
            "Creating service revision for tutor: "
            f"{tutor_id} / {service_name} / {level.value}"
        )
        revision_response = await ServiceRepository().create_service(service_payload)
        service_revision = response_data(revision_response)
        print(f"Pending service revision created: {service_revision.id}")

        print(f"Approving service revision: {service_revision.id}")
        approval_response = await ServiceRepository().approve_revision(
            UUID(str(service_revision.id)), admin_user_id
        )
        approved_services.append(response_data(approval_response))

    return approved_services


async def main() -> None:
    print_heading("SkillBridge Database Seeder")
    await reset_database_schema()

    admin_role = await create_role_if_missing(
        title=ROLE_ENUM.ADMIN,
        slug="admin",
        description="Administrator role",
    )
    tutor_role = await create_role_if_missing(
        title=ROLE_ENUM.TUTOR,
        slug="tutor",
        description="Tutor role",
    )
    student_role = await create_role_if_missing(
        title=ROLE_ENUM.STUDENT,
        slug="student",
        description="Student role",
    )

    # Keep exactly one administrator with the original credentials.
    admin_user = await create_user(
        full_name="Admin User",
        email="admin@hs-fulda.de",
        password="AdminPass123!",
        role_id=admin_role.id,
    )
    print(f"Admin created: {admin_user.id}")

    tutors = []
    for index, profile in enumerate(TUTOR_PROFILES, start=1):
        full_name, program, bio, teaching_style, tags = profile
        tutor = await create_user(
            full_name=full_name,
            email=f"tutor{index}@hs-fulda.de",
            password="TutorPass123!",
            role_id=tutor_role.id,
            phone=f"+49 151 2000{index:04d}",
            academic_program=program,
            bio=bio,
            teaching_style=teaching_style,
            is_visible=index % 10 != 0,
            accepting_requests=index % 6 != 0,
            tags=tags,
        )
        print(f"Tutor created: {tutor.id}")
        tutors.append(tutor)

    students = []
    for index, full_name in enumerate(STUDENT_NAMES, start=1):
        student = await create_user(
            full_name=full_name,
            email=f"student{index}@hs-fulda.de",
            password="StudentPass123!",
            role_id=student_role.id,
            field_of_study=STUDENT_FIELDS[(index - 1) % len(STUDENT_FIELDS)],
            enrolled_university=UNIVERSITIES[(index - 1) % len(UNIVERSITIES)],
            graduation_year=2026 + ((index - 1) % 6),
        )
        print(f"Student created: {student.id}")
        students.append(student)

    approved_tutor_revisions = await approve_all_tutor_revisions(admin_user.id)
    print(f"Approved {len(approved_tutor_revisions)} tutor revisions.")

    approved_tutor_ids = [
        UUID(str(revision["tutor_id"])) for revision in approved_tutor_revisions
    ]
    approved_service_count = 0
    for tutor_index, tutor_id in enumerate(approved_tutor_ids):
        approved_services = await create_and_approve_services_for_tutor(
            tutor_id=tutor_id,
            tutor_index=tutor_index,
            admin_user_id=admin_user.id,
            count=6,
        )
        approved_service_count += len(approved_services)

    print_heading("Database seeding complete")
    print("Admin created: 1")
    print(f"Tutors created: {len(tutors)}")
    print(f"Students created: {len(students)}")
    print(f"Services created and approved: {approved_service_count}")
    print("Admin credentials: admin@hs-fulda.de / AdminPass123!")
    print(
        f"Tutor credentials: tutor1@hs-fulda.de..tutor{len(tutors)}@hs-fulda.de "
        "/ TutorPass123!"
    )
    print(
        "Student credentials: "
        f"student1@hs-fulda.de..student{len(students)}@hs-fulda.de "
        "/ StudentPass123!"
    )


async def run() -> None:
    try:
        await main()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
