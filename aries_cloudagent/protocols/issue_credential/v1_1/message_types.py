PROTOCOL_URI = "https://didcomm.org/issue-credential/1.1"
PROTOCOL_PACKAGE = "aries_cloudagent.protocols.issue_credential.v1_1"

CREDENTIAL_ISSUE = f"{PROTOCOL_URI}/issue-credential"

MESSAGE_TYPES = {
    CREDENTIAL_ISSUE: (f"{PROTOCOL_PACKAGE}.messages.credential_issue.CredentialIssue"),
}