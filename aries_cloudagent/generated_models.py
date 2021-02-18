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





class NewApplication(OpenAPISchema):
    user_data = fields.Dict(keys=fields.String(), values=fields.String(), required=True)
    service_uuid = fields.String(required=True)





class Application(OpenAPISchema):
    appliance_uuid = fields.String(required=True)
    updated_at = fields.String(required=True)
    created_at = fields.String(required=True)
    connection_uuid = fields.String(required=True)
    service_uuid = fields.String(required=True)
    consent = fields.Nested(lambda: OCASchemaDRIDataTuple(), required=True)
    service = fields.Nested(lambda: OCASchema(), required=True)





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
    client_id = fields.String()
    client_secret = fields.String()
    instance_name = fields.String()





class PDSSettingDriver(OpenAPISchema):
    name = fields.String(required=True, validate=[OneOf(choices=['own_your_data', 'thcf_data_vault', 'local'], labels=[])])
    thcf_data_vault = fields.Nested(lambda: PDSSettingDriverThcf_data_vault())
    own_your_data = fields.Nested(lambda: PDSSettingDriverOwn_your_data())
    local = fields.Nested(lambda: PDSSettingDriverLocal())





class PDSSettingDriverLocal(OpenAPISchema):
    test = fields.String()





class PDSSettingDriverOwn_your_data(OpenAPISchema):
    grant_type = fields.String(required=True, validate=[OneOf(choices=['client_credentials'], labels=[])])





class PDSSettingDriverThcf_data_vault(OpenAPISchema):
    host = fields.String(required=True, description='Server URL')





class PDSDriverStatus(OpenAPISchema):
    connected = fields.Boolean(required=True)
    driver = fields.String(required=True)
    instance_name = fields.String(required=True)
    exception = fields.String()





class ArrayOfPDSDriverStatuses(PDSDriverStatus):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






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






class OCASchema(OpenAPISchema):
    oca_schema_dri = fields.String(required=True)





class OCASchemaDRIDataTuple(OCASchema):
    oca_data = fields.Dict(keys=fields.String(), values=fields.String(), required=True)





class Consent(OCASchemaDRIDataTuple):
    label = fields.String(required=True)
    consent_uuid = fields.String(required=True, allow_none=True)





class Service(OpenAPISchema):
    label = fields.String(required=True)
    updated_at = fields.String(allow_none=True)
    created_at = fields.String(allow_none=True)
    service_schema_dri = fields.String(required=True, description='OCA Schema DRI')





class DefinedService(Service):
    consent = fields.Nested(lambda: OCASchemaDRIDataTuple(), required=True)





class ArrayOfDefinedServices(DefinedService):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)






class NewService(Service):
    consent_uuid = fields.String(required=True)





class RequestServiceList(OpenAPISchema):
    result = fields.String(required=True)





class Payload(OpenAPISchema):
    payload = fields.String(required=True)





class DRIResponse(OpenAPISchema):
    dri = fields.String(required=True)


