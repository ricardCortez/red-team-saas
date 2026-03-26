"""Integration registry — Phase 16"""
from app.services.integrations.slack_integration   import SlackIntegration
from app.services.integrations.github_integration  import GitHubIntegration
from app.services.integrations.jira_integration    import JiraIntegration
from app.services.integrations.webhook_integration import WebhookIntegration

INTEGRATION_CLASSES = {
    "slack":   SlackIntegration,
    "github":  GitHubIntegration,
    "jira":    JiraIntegration,
    "webhook": WebhookIntegration,
    # "teams":   TeamsIntegration,    # TODO Phase 17+
    # "discord": DiscordIntegration,  # TODO Phase 17+
}

__all__ = [
    "INTEGRATION_CLASSES",
    "SlackIntegration",
    "GitHubIntegration",
    "JiraIntegration",
    "WebhookIntegration",
]
