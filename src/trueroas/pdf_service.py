import uuid
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

from trueroas.core.config import settings


class PDFService:
    """
    Handles PDF generation using WeasyPrint with template caching via Jinja2.
    """

    def __init__(self) -> None:
        # Template directory at project root
        self.template_dir = (settings.BASE_DIR / "templates").resolve()
        self.template_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment with caching enabled
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            cache_size=100,  # Enables template caching
        )

    def generate_report(self, tenant_id: str, data: Dict[str, Any]) -> str:
        """
        Renders an HTML template and converts it to a PDF stored in the tenant's directory.
        """
        # 1. Render the HTML content from template
        # audit_report.html must exist in the templates directory
        try:
            template = self.env.get_template("audit_report.html")
        except Exception:
            # Log error and raise specific exception for Celery worker to catch
            raise FileNotFoundError(
                "Strategy PDF template 'audit_report.html' not found in templates directory."
            )

        html_content = template.render(**data)

        # 2. Determine and create storage path
        report_uuid = str(uuid.uuid4())
        storage_root = (settings.BASE_DIR / settings.SQLITE_PATH).resolve()
        tenant_reports_dir = (storage_root / tenant_id / "reports").resolve()

        # Path traversal guard: Ensure the tenant reports directory stays within storage root
        if not str(tenant_reports_dir).startswith(str(storage_root)):
            raise PermissionError(
                f"Security: Blocked unauthorized path access for tenant: {tenant_id}"
            )

        tenant_reports_dir.mkdir(parents=True, exist_ok=True)
        report_file_path = tenant_reports_dir / f"{report_uuid}.pdf"

        # 3. Generate PDF using WeasyPrint (lazy import: GTK only required at render time)
        from weasyprint import HTML

        HTML(string=html_content, base_url=str(settings.BASE_DIR)).write_pdf(
            target=str(report_file_path)
        )

        return str(report_file_path)


pdf_service = PDFService()
