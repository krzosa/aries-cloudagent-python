"""This file is auto generated"""
from marshmallow import ( Schema, fields, EXCLUDE )

class OpenAPISchema(Schema):
    class Meta:
        unknown = EXCLUDE

    
class ServiceExchangeRecord(OpenAPISchema):
    label = fields.String(required=True)
    service_id = fields.String(required=True)





class ServiceExchangeRecordResponse(OpenAPISchema):
    result = fields.List(fields.Nested(lambda: ServiceExchangeRecord()), required=True)





class PDSSettingsExample(OpenAPISchema):
    client_id = fields.String(missing=lambda: '1321wrf1g3f1412rsrfer')
    client_secret = fields.String(missing=lambda: '12341551513qw42as')
    optional_instance_name = fields.String(missing=lambda: 'default')
    grant_type = fields.String(missing=lambda: 'client_credentials')





class PDSGetSettingsSchemaResponse(OpenAPISchema):
    pds_name_1 = fields.Nested(lambda: PDSSettingsExample())
    pds_name_2 = fields.Field()





class PDSResponse(OpenAPISchema):
    active_pds = fields.String(required=True)
    types = fields.List(fields.Nested(lambda: PDSResponseTypesItem()), required=True)





class PDSResponseTypesItem(OpenAPISchema):
    local = fields.Nested(lambda: OCASchema())
    pds_name = fields.Nested(lambda: OCASchema())





class PDSPostCurrent(OpenAPISchema):
    data = fields.Nested(lambda: PDSPostCurrentData(), required=True)





class PDSPostCurrentData(OpenAPISchema):
    n511f1t10iomj01tyf = fields.Field(data_key='511f1t10iomj01tyf')
    okm12_0goi2mj3oig = fields.Field(data_key='okm12-0goi2mj3oig')





class ServiceAdd(OpenAPISchema):
    label = fields.String(required=True)
    service_schema = fields.Nested(lambda: OCASchema(), required=True)
    consent_id = fields.String(required=True)





class ServiceApply(OpenAPISchema):
    user_data = fields.String(required=True)
    connection_id = fields.String(required=True)
    service_id = fields.String(required=True)





class OCAData(OpenAPISchema):
    oca_schema_namespace = fields.String(required=True)
    oca_schema_dri = fields.String(required=True)
    oca_data = fields.Field(required=True)





class DefineConsent(OCAData):
    label = fields.String(required=True)





class Consent(DefineConsent):
    consent_id = fields.String(required=True)





class ProcessApplication(OpenAPISchema):
    exchange_record_id = fields.String(required=True)
    decision = fields.String(required=True)





class Service(OpenAPISchema):
    service_id = fields.String(required=True)
    label = fields.String(required=True)





class RequestServiceList(OpenAPISchema):
    result = fields.String(required=True)





class OCASchema(OpenAPISchema):
    oca_schema_namespace = fields.String(required=True)
    oca_schema_dri = fields.String(required=True)





class Payload(OpenAPISchema):
    payload = fields.String(required=True)





class DRIResponse(OpenAPISchema):
    dri = fields.String(required=True)


