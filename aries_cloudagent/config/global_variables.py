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
CONSENT_GIVEN_DRI = "oca_schema_dri_consent_given"
