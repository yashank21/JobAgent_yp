from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class SourceType(Enum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    WORKDAY = "workday"

@dataclass
class CompanyConfig:
    id: str
    name: str
    source_type: SourceType
    config_params: dict[str, Any] = field(default_factory=dict)
    active_in_india: bool = True

# Bulk curated list of top MNCs, MAANG, and tech unicorns with active India R&D boards
MASSIVE_INDIA_TECH_COMPANIES = [
    # --- GREENHOUSE GIANTS & UNICORNS ---
    CompanyConfig("postman", "Postman", SourceType.GREENHOUSE, {"board_token": "postman"}),
    CompanyConfig("phonepe", "PhonePe", SourceType.GREENHOUSE, {"board_token": "phonepe"}),
    CompanyConfig("mongodb", "MongoDB", SourceType.GREENHOUSE, {"board_token": "mongodb"}),
    CompanyConfig("cloudflare", "Cloudflare", SourceType.GREENHOUSE, {"board_token": "cloudflare"}),
    CompanyConfig("databricks", "Databricks", SourceType.GREENHOUSE, {"board_token": "databricks"}),
    CompanyConfig("gitlab", "GitLab", SourceType.GREENHOUSE, {"board_token": "gitlab"}),
    CompanyConfig("coinbase", "Coinbase", SourceType.GREENHOUSE, {"board_token": "coinbase"}),
    CompanyConfig("stripe", "Stripe", SourceType.GREENHOUSE, {"board_token": "stripe"}),
    CompanyConfig("pinterest", "Pinterest", SourceType.GREENHOUSE, {"board_token": "pinterest"}),
    CompanyConfig("figma", "Figma", SourceType.GREENHOUSE, {"board_token": "figma"}),
    CompanyConfig("instawork", "Instawork", SourceType.GREENHOUSE, {"board_token": "instawork"}),
    CompanyConfig("scaleai", "Scale AI", SourceType.GREENHOUSE, {"board_token": "scaleai"}),
    CompanyConfig("anthropic", "Anthropic", SourceType.GREENHOUSE, {"board_token": "anthropic"}),
    CompanyConfig("airbnb", "Airbnb", SourceType.GREENHOUSE, {"board_token": "airbnb"}),
    CompanyConfig("discord", "Discord", SourceType.GREENHOUSE, {"board_token": "discord"}),
    CompanyConfig("brex", "Brex", SourceType.GREENHOUSE, {"board_token": "brex"}),
    CompanyConfig("asana", "Asana", SourceType.GREENHOUSE, {"board_token": "asana"}),
    CompanyConfig("faire", "Faire", SourceType.GREENHOUSE, {"board_token": "faire"}),

    # --- LEVER GIANTS & TECH FIRMS ---
    CompanyConfig("browserstack", "BrowserStack", SourceType.LEVER, {"board_token": "browserstack"}),
    CompanyConfig("clevertap", "CleverTap", SourceType.LEVER, {"board_token": "clevertap"}),
    CompanyConfig("atlassian", "Atlassian", SourceType.LEVER, {"board_token": "atlassian"}),
    CompanyConfig("netflix", "Netflix", SourceType.LEVER, {"board_token": "netflix"}),
    CompanyConfig("canonical", "Canonical", SourceType.LEVER, {"board_token": "canonical"}),
    CompanyConfig("hashicorp", "HashiCorp", SourceType.LEVER, {"board_token": "hashicorp"}),
    CompanyConfig("olx", "OLX Group", SourceType.LEVER, {"board_token": "olx"}),
    CompanyConfig("zeptomail", "Zoho / Zepto", SourceType.LEVER, {"board_token": "zoho"}),

    # --- ASHBY HIGH-GROWTH UNICORNS ---
    CompanyConfig("zepto", "Zepto", SourceType.ASHBY, {"board_token": "zeptonow"}),
    CompanyConfig("meesho", "Meesho", SourceType.ASHBY, {"board_token": "meesho"}),
    CompanyConfig("postman_ashby", "Postman (Alt)", SourceType.ASHBY, {"board_token": "postman"}),

    # --- WORKDAY BOARDS ---
    CompanyConfig("workday", "Workday", SourceType.WORKDAY, {
        "tenant": "workday",
        "site_name": "Workday",
        "tier": "wd5",
    }),
]

class IndiaCompanyRegistry:
    def __init__(self, companies: list[CompanyConfig] = None):
        self.companies = companies or MASSIVE_INDIA_TECH_COMPANIES

    def get_active_india(self) -> list[CompanyConfig]:
        return [c for c in self.companies if c.active_in_india]

def get_india_registry():
    return IndiaCompanyRegistry()