{
    "name": "Employee Documents",
    "summary": """Manages Employee Documents With Expiry Notifications.""",
    "description": """Manages Employee Related Documents with Expiry Notifications.""",
    "category": "Odex25-HR/Odex25-HR",
    "author": "Expert Co. Ltd.",
    "website": "http://exp-sa.com",
    "depends": ["base", "hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "data/ir_cron.xml",
        "data/mail_template.xml",
        "views/employee_check_list_view.xml",
        "views/employee_document_view.xml",
    ],
}
