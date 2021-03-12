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

    
class ArrayOfCredentialDRIItem(OpenAPISchema):
    dri = fields.String(required=True)


class ArrayOfCredentialDRI(ArrayOfCredentialDRIItem):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class PresentationRequest(OpenAPISchema):
    uuid = fields.UUID(allow_none=True)
    oca_schema_dri = fields.String(required=True)
    connection_uuid = fields.String(required=True)


class ArrayOfPresentationRequests(PresentationRequest):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class Presentation(OpenAPISchema):
    presentation = fields.Dict(keys=fields.String(), values=fields.String())
    connection_uuid = fields.String()


class ArrayOfPresentations(Presentation):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class PDSActivate(OpenAPISchema):
    instance_name = fields.String(required=True)
    driver = fields.String(required=True, validate=[OneOf(choices=['own_your_data_data_vault', 'own_your_data_sem_con', 'thcf_data_vault', 'local'], labels=[])])


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
    name = fields.String(required=True, validate=[OneOf(choices=['own_your_data_data_vault', 'own_your_data_sem_con', 'thcf_data_vault', 'local'], labels=[])])
    thcf_data_vault = fields.Nested(lambda: PDSSettingDriverThcf_data_vault())
    own_your_data_data_vault = fields.Nested(lambda: PDSSettingDriverOwn_your_data_data_vault())
    own_your_data_sem_con = fields.Nested(lambda: PDSSettingDriverOwn_your_data_sem_con())
    local = fields.Nested(lambda: PDSSettingDriverLocal())


class PDSSettingDriverLocal(OpenAPISchema):
    test = fields.String()


class PDSSettingDriverOwn_your_data_sem_con(OpenAPISchema):
    scope = fields.String(required=True, validate=[OneOf(choices=['admin', 'write', 'read'], labels=[])])
    grant_type = fields.String(required=True, validate=[OneOf(choices=['client_credentials'], labels=[])])


class PDSSettingDriverOwn_your_data_data_vault(OpenAPISchema):
    grant_type = fields.String(required=True, validate=[OneOf(choices=['client_credentials'], labels=[])])


class PDSSettingDriverThcf_data_vault(OpenAPISchema):
    host = fields.String(required=True, description='Server URL')


class PDSDriver(OpenAPISchema):
    name = fields.String(validate=[OneOf(choices=['own_your_data_data_vault', 'own_your_data_sem_con', 'thcf_data_vault', 'local'], labels=[])])
    oca_schema_dri = fields.String()


class ArrayOfPDSDrivers(PDSDriver):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class ArrayOfPDSSettings(PDSSetting):
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
    dri = fields.String()


class ArrayOfConsents(Consent):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class Document(OpenAPISchema):
    xcontext = fields.List(fields.String(), data_key='@context')
    issuanceDate = fields.String()
    issuer = fields.String()
    proof = fields.Nested(lambda: DocumentProof())
    type = fields.List(fields.String())
    credentialSubject = fields.Nested(lambda: DocumentCredentialSubject())


class ArrayOfDocuments(Document):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class DocumentCredentialSubject(AdditionalPropertiesSchema):
    subject_id = fields.String()
    type = fields.String()

    class Meta:
        additional_field = fields.Dict(keys=fields.String(), values=fields.String())



class DocumentType(PrimitiveValueSchema):
    class schema_class(OpenAPISchema):
        value = fields.List(fields.String())



class DocumentProof(OpenAPISchema):
    created = fields.String()
    jws = fields.String()
    proofPurpose = fields.String()
    type = fields.String()
    verificationMethod = fields.String()


class Documentxcontext(PrimitiveValueSchema):
    class schema_class(OpenAPISchema):
        value = fields.List(fields.String())



class BaseService(OpenAPISchema):
    consent_dri = fields.String(required=True)
    service_schema_dri = fields.String(required=True)
    label = fields.String(required=True)


class Service(BaseService):
    service_uuid = fields.UUID(required=True)
    updated_at = fields.String(allow_none=True)
    created_at = fields.String(allow_none=True)
    label = fields.String(required=True)
    service_schema_dri = fields.String(required=True, description='OCA Schema DRI')


class ArrayOfServices(Service):
    def __init__(self, *args, **kwargs):
        kwargs['many'] = True
        super().__init__(*args, **kwargs)



class Payload(OpenAPISchema):
    payload = fields.String(required=True)


class DRIResponse(OpenAPISchema):
    dri = fields.String(required=True)


class Error(OpenAPISchema):
    message = fields.String()
    code = fields.String()
    payload = fields.List(fields.String())


class ErrorPayload(PrimitiveValueSchema):
    class schema_class(OpenAPISchema):
        value = fields.List(fields.String())



class ApplicationsMineInput:
    class Get:
        """
        Queries for all pending applications that I have applied to
        """

        pass



class ApplicationsOthersInput:
    class Get:
        """
        Queries for all pending applications that others applied to
        """

        pass



class ApplicationsApplianceUuidAcceptInput:
    class Put:
        class Path(OpenAPISchema):
            appliance_uuid = fields.Field(required=True)




class ApplicationsApplianceUuidRejectInput:
    class Put:
        class Path(OpenAPISchema):
            appliance_uuid = fields.Field(required=True)




class PdsSettingsInput:
    class Post:
        """
        Set the configuration of pds instances and/or create pds instances
        """

        pass

    class Get:
        """
        Query settings of all currently setup PDSes
        """

        pass



class PdsActivateInput:
    class Post:
        """
        Choose a PDS for all the saving operations
        """

        pass



class PdsActiveInput:
    class Get:
        pass



class PdsDriversInput:
    class Get:
        """
        Get all registered PDSes and current active PDS
        """

        pass



class PdsOcaschemachunksInput:
    class Get:
        """
        Retrieve data in bulk
        """

        class Query(OpenAPISchema):
            oca_schema_dris = fields.Field()


    class Post:
        """
        Post data in bulk
        """

        pass



class ConsentsInput:
    class Post:
        """
        Define a new consent
        """

        pass

    class Get:
        """
        Retrieve all defined consents
        """

        pass



class ConsentsConsentDriInput:
    class Delete:
        """
        Removes consent by its uuid
        """

        class Path(OpenAPISchema):
            consent_dri = fields.Field(required=True)




class ConnectionsConnectionUuidServicesInput:
    class Get:
        """
        Request a service list from other agent
        """

        class Path(OpenAPISchema):
            connection_uuid = fields.Field(required=True)




class ServicesInput:
    class Get:
        """
        Retrieve service by id
        """

        pass



class ServicesServiceUuidInput:
    class Get:
        """
        Retrieve service by id
        """

        class Path(OpenAPISchema):
            service_uuid = fields.Field(required=True)


    class Delete:
        """
        Removes service by its uuid
        """

        class Path(OpenAPISchema):
            service_uuid = fields.Field(required=True)




class ServicesAddInput:
    class Post:
        """
        Define a new service
        """

        pass



class ServicesApplyInput:
    class Post:
        """
        Apply to other agent's service
        """

        pass



class DocumentsGivenconsentsInput:
    class Get:
        """
        Retrieve all consents given to other agent's
        """

        pass



class DocumentsMineconsentsInput:
    class Get:
        """
        Retrieve all consents I have received
        """

        pass



class DocumentsGivenpresentationsInput:
    class Get:
        """
        Retrieve all presentations given to other agent's
        """

        pass



class DocumentsMinepresentationsInput:
    class Get:
        """
        Retrieve all presentations I have received
        """

        pass



class DocumentsGivenInput:
    class Get:
        """
        Retrieve all documents given to other agent's
        """

        pass



class DocumentsMineInput:
    class Get:
        """
        Retrieve all documents I have received or created
        """

        pass



class PresentationrequestsInput:
    class Get:
        """
        Retrieves all presentations requests that are addressed to me.
        """

        pass

    class Post:
        """
        Request my agent to send a presentation request to another agent
        """

        pass



class PresentationrequestsPresentationRequestUuidMatchingdocumentsInput:
    class Get:
        """
        Retrieves all presentations requests that are addressed to me.
        """

        class Path(OpenAPISchema):
            presentation_request_uuid = fields.Field(required=True)




class PresentationrequestsPresentationRequestUuidAcceptInput:
    class Put:
        """
        Accepts given presentation request
        """

        class Path(OpenAPISchema):
            presentation_request_uuid = fields.Field(required=True)




class PresentationrequestsPresentationRequestUuidRejectInput:
    class Put:
        """
        Rejects given presentation request
        """

        class Path(OpenAPISchema):
            presentation_request_uuid = fields.Field(required=True)




class PresentationsInput:
    class Get:
        """
        Request my agent to send a presentation request to another agent
        """

        pass



class PresentationsPresentationUuidAcceptInput:
    class Put:
        """
        Accepts given presentation, which in return provides confirmation VC.
        """

        class Path(OpenAPISchema):
            presentation_uuid = fields.Field(required=True)




class PresentationsPresentationUuidRejectInput:
    class Put:
        """
        Rejects given presentation, which in return provides confirmation VC.
        """

        class Path(OpenAPISchema):
            presentation_uuid = fields.Field(required=True)
