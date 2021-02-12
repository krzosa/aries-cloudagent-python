"""This file is auto generated"""
from marshmallow import ( Schema, fields, EXCLUDE )
from marshmallow.validate import OneOf
from marshmallow import Schema, SchemaOpts, fields, ValidationError
from marshmallow import pre_load, pre_dump


class PrimitiveValueSchema:
    schema_class = None
    key = "value"
    missing_value = None

    def __init__(self, *args, **kwargs):
        self.schema = self.__class__.schema_class(*args, **kwargs)

    def _fix_exception(self, exc):  # xxx: side effect
        if hasattr(exc, "data") and self.key in exc.data:
            exc.data = exc.data[self.key]
        if (
            hasattr(exc, "messages")
            and hasattr(exc.messages, "keys")
            and self.key in exc.messages
        ):
            exc.messages = exc.messages[self.key]
            exc.args = tuple([exc.messages, *exc.args[1:]])
        if hasattr(exc, "valid_data") and self.key in exc.valid_data:
            exc.valid_data = exc.valid_data[self.key]
        return exc

    def load(self, value):  # don't support many
        try:
            r = self._do_load(value)
        except ValidationError as e:
            self._fix_exception(e)
            raise e.with_traceback(e.__traceback__)
        return r.get(self.key) or self.missing_value

    def _do_load(self, value):
        data = {self.key: value}
        return self.schema.load(data)

    def dump(self, value):  # don't support many
        try:
            r = self._do_dump(value)
        except ValidationError as e:
            self._fix_exception(e)
            raise e.with_traceback(e.__traceback__)
        return r.get(self.key) or self.missing_value

    def _do_dump(self, value):
        data = {self.key: value}
        return self.schema.dump(data)


class AdditionalPropertiesOpts(SchemaOpts):
    def __init__(self, meta, **kwargs):
        super().__init__(meta, **kwargs)
        self.additional_field = getattr(meta, "additional_field", fields.Field)


def make_additional_properties_schema_class(Schema):
    class AdditionalPropertiesSchema(Schema):
        """
        support addtionalProperties
        class MySchema(AdditionalPropertiesSchema):
            class Meta:
                additional_field = fields.Integer()
        """

        OPTIONS_CLASS = AdditionalPropertiesOpts

        @pre_load
        def wrap_load_dynamic_additionals(self, data, *, many=False, partial=False):
            diff = set(data.keys()).difference(self.load_fields.keys())
            for name in diff:
                f = self.opts.additional_field
                self.load_fields[name] = f() if callable(f) else f
            return data

        @pre_dump
        def wrap_dump_dynamic_additionals(self, data, *, many=False, partial=False):
            diff = set(data.keys()).difference(self.dump_fields.keys())
            for name in diff:
                f = self.opts.additional_field
                self.dump_fields[name] = f() if callable(f) else f
            return data

    return AdditionalPropertiesSchema


AdditionalPropertiesSchema = make_additional_properties_schema_class(Schema)

class OpenAPISchema(Schema):
    class Meta:
        unknown = EXCLUDE

    
class PDSActivate(OpenAPISchema):
    instance_name = fields.String(required=True)
    driver = fields.String(required=True, validate=[OneOf(choices=['own_your_data', 'local', 'thcf_data_vault'], labels=[])])





class Application(OpenAPISchema):
    appliance_uuid = fields.String(required=True)
    updated_at = fields.String(required=True)
    created_at = fields.String(required=True)
    connection_uuid = fields.String(required=True)
    service_uuid = fields.String(required=True)
    consent = fields.Nested(lambda: ConsentSerialized(), required=True)
    service = fields.Nested(lambda: OCAData(), required=True)





class ArrayOfApplications(Application):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class MineApplication(Application):
    service_user_data = fields.String(required=True, description='JSON serialized service application data')





class ArrayOfMineApplications(MineApplication):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class PDSSetting(OpenAPISchema):
    driver = fields.Nested(lambda: PDSSettingDriver(), required=True)
    client_id = fields.String(required=True)
    client_secret = fields.String(required=True)
    instance_name = fields.String()





class PDSSettingDriver(OpenAPISchema):
    name = fields.String(required=True, validate=[OneOf(choices=['own_your_data', 'thcf_data_vault', 'local'], labels=[])])
    thcf_data_vault = fields.Nested(lambda: PDSSettingDriverThcf_data_vault())
    own_your_data = fields.Nested(lambda: PDSSettingDriverOwn_your_data())





class PDSSettingDriverOwn_your_data(OpenAPISchema):
    scope = fields.String(required=True, validate=[OneOf(choices=['admin', 'write', 'read'], labels=[])])
    grant_type = fields.String(required=True, validate=[OneOf(choices=['client_credentials'], labels=[])])





class PDSSettingDriverThcf_data_vault(OpenAPISchema):
    host = fields.String(required=True, description='Server URL')





class ArrayOfPDSSettings(PDSSetting):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class PDSDriver(OpenAPISchema):
    name = fields.String(validate=[OneOf(choices=['own_your_data', 'thcf_data_vault', 'local'], labels=[])])
    oca_schema_dri = fields.String()





class ArrayOfPDSDrivers(PDSDriver):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class PDSDriverInstance(OpenAPISchema):
    instance_name = fields.String()
    driver = fields.Nested(lambda: PDSDriver())





class OCASchemaChunk(OpenAPISchema):
    dri = fields.String(required=True)
    payload = fields.List(fields.Nested(lambda: OCASchemaChunkPayloadItem()), required=True)





class ArrayOfOCASchemaChunks(OCASchemaChunk):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class OCASchemaChunkPayloadItem(AdditionalPropertiesSchema):

    class Meta:
        additional_field = fields.String()



class OCASchemaChunkPayload(OCASchemaChunkPayloadItem):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class ServiceAdd(OpenAPISchema):
    label = fields.String(required=True)
    service_schema = fields.Nested(lambda: OCASchema(), required=True)
    consent_id = fields.String(required=True)





class ServiceApply(OpenAPISchema):
    user_data = fields.String(required=True)
    connection_id = fields.String(required=True)
    service_id = fields.String(required=True)





class OCASchema(OpenAPISchema):
    oca_schema_namespace = fields.String(required=True)
    oca_schema_dri = fields.String(required=True)





class OCAData(OCASchema):
    oca_data_dri = fields.String(required=True)





class OCADataSerialized(OCAData):
    oca_data = fields.Field(required=True)





class ConsentSerialized(OCADataSerialized):
    usage_policy = fields.String()





class Consent(OCAData):
    label = fields.String(required=True)
    consent_id = fields.String(required=True)





class ProcessApplication(OpenAPISchema):
    exchange_record_id = fields.String(required=True)
    decision = fields.String(required=True)





class Service(OpenAPISchema):
    service_id = fields.String(required=True)
    label = fields.String(required=True)
    updated_at = fields.String()
    created_at = fields.String()
    service_schema = fields.Nested(lambda: OCASchema())
    consent_schema = fields.Nested(lambda: ConsentSerialized())





class RequestServiceList(OpenAPISchema):
    result = fields.String(required=True)





class Payload(OpenAPISchema):
    payload = fields.String(required=True)





class DRIResponse(OpenAPISchema):
    dri = fields.String(required=True)


