USAGE_POLICY_VERIFY = "https://governance.ownyourdata.eu/api/usage-policy/match"
USAGE_POLICY_PARSE = "https://governance.ownyourdata.eu/api/usage-policy/parse"
OYD_OCA_CHUNKS_PREFIX = "tda.oca_chunks."
REGISTERED_PDS = {
    "personal_storage_registered_types": {
        "local": "aries_cloudagent.pdstorage_thcf.local.LocalPDS",
        "thcf_data_vault": "aries_cloudagent.pdstorage_thcf.thcf_data_vault.DataVault",
        "own_your_data_data_vault": "aries_cloudagent.pdstorage_thcf.own_your_data_data_vault.OwnYourDataVault",
    }
}
CONSENT_DRI = "consent_dri"
ACK_CREDENTIAL_DRI = "bCN4tzZssT4sDDFFTh5AmoesdQeeTSyjNrQ6gxnCerkn"


CREDENTIALS_TABLE = "credentials"
CONSENT_FROM_APPLICANT_DRI = "consent_from_applicant"
DOCUMENTS_MINE = [CREDENTIALS_TABLE, CONSENT_FROM_APPLICANT_DRI]

CREDENTIALS_GIVEN_DRI = "credentials_given"
CONSENT_GIVEN_DRI = "oca_schema_dri_consent_given"
ACKS_GIVEN_DRI = "ack"
PRESENTATION_GIVEN_DRI = "presentation_given"
DOCUMENTS_GIVEN = [
    CONSENT_GIVEN_DRI,
    CREDENTIALS_GIVEN_DRI,
    ACKS_GIVEN_DRI,
    PRESENTATION_GIVEN_DRI,
]
