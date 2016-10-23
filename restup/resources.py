from django.core.paginator import Paginator, InvalidPage
from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth import get_user_model

from .serializers import JsonSerializer
from .constants import (OK, CREATED, NO_CONTENT, METHOD_NOT_ALLOWED,
                        UNAUTHORIZED, NOT_FOUND, FORBIDDEN, BAD_REQUEST, ERROR)


class ModelResource(object):

    SAFE_METHODS = ("GET", )

    ALL_METHODS = ("GET", "POST", "PUT", "DELETE")

    ACTIONS = {
        "list": {
            "GET": "list",
            "POST": "create",
        },
        "detail": {
            "GET": "detail",
            "PUT": "update",
            "DELETE": "delete"
        },
        "list_schema": {
            "GET": "list_schema"
        },
        "detail_schema": {
            "GET": "detail_schema"
        }
    }

    STATUS_MAP = {
        'list': OK,
        'detail': OK,
        'create': CREATED,
        'update': OK,
        'delete': NO_CONTENT
    }

    model = None
    per_page = 10
    paginator_class = Paginator
    serializer = JsonSerializer()
    schema = {}
    allowed_methods = ALL_METHODS

    def __init__(self, *args, **kwargs):
        self.initargs = args
        self.initkwargs = kwargs
        self.request = None
        self.data = None
        self.action = None

    @classmethod
    def urls(cls):
        """
        Class method used to route the request to the correct action handler.
        The action handler works in a very similar way compared to how the
        Base Django generic view class works.

        :return: A list of url route configuration objects.
        :type return: list
        """
        return [
            url(
                r'^$',
                cls.as_list()
            ),
            url(
                r'^(?P<pk>\w[\w/-]*)/$',
                cls.as_detail()
            )
        ]

    @classmethod
    def as_list(cls, *initargs, **initkwargs):
        """
        Handles all incoming requests to any list action type endpoint. Passes
        action type and init arguments to the `dispatch` class method.

        :param initargs: Optional positional initialization arguments.

        :param initkwargs: Optional keyword initialization arguments.

        :return: A call do the `dispatch` method wrapped in a `csrf_exempt`
        decorator.
        """
        return csrf_exempt(cls.dispatch(
            'list',
            *initargs,
            **initkwargs
        ))

    @classmethod
    def as_detail(cls, *initargs, **initkwargs):
        """
        Handles all incoming requests to detail action type endpoints. Passes
        the necessary data to the `dispatch` class method.

        :param initargs: Optional positional initialization arguments.

        :param initkwargs: Optional keyword initialization arguments.

        :return: A call to the `dispatch` class method wrapped in the
        `csrf_exempt` decorator.
        """
        return csrf_exempt(cls.dispatch(
            'detail',
            *initargs,
            **initkwargs
        ))

    @classmethod
    def dispatch(cls, action=None, *initargs, **initkwargs):
        """
        Method that creates a wrapper function in order to create an instance
        of the model resource class.

        :param action: A string representing the action the request is trying
        to perform on the resource.
        :type action: str

        :param initargs: Optional positional initialization arguments.

        :param initkwargs: Optional keyword initialization arguments.

        :return: A view function that returns a call to the `route` method
        after initializing the <ModelResource> class. This is the function the
        Django router hands the actual request object off to.
        """

        def view(request, *args, **kwargs):
            self = cls(*initargs, **initkwargs)
            self.request = request
            self.action = action
            return self.route(action, *args, **kwargs)

        return view

    def route(self, action, *args, **kwargs):
        """
        This method performs some basic initial permissions checks on the
        request. It then populates the `self.data` attribute before passing
        the torch to the determined action handler.

        :param action: The action the request is trying to perform.

        :return: A call to an action handler.
        """
        request_method = self.request_method()
        if not self.method_check(request_method):
            return HttpResponse(
                status=METHOD_NOT_ALLOWED
            )
        if not self.is_authenticated(self.request):
            return HttpResponse(
                status=UNAUTHORIZED
            )
        self.data = self.deserialize(action, self.request_body())
        view_method_name = self.ACTIONS[action][request_method]
        view = getattr(self, view_method_name)
        return view(*args, **kwargs)

    def request_method(self):
        """
        Convenience method for returning the Http Request method.

        :return: Http Request method.
        :type return: str
        """
        return self.request.method

    def request_body(self):
        """
        Convenience method for getting the request body as a string.

        :return: Http request body as a byte string.
        :type return: str
        """
        return self.request.body

    def method_check(self, method):
        """
        Checks to make sure the request method is in the list of allowed
        methods. Default allows GET, POST, PUT, DELETE, OPTIONS.

        :param method: A string representing the request method.
        :type method: str

        :return: True if the request should be allowed, false otherwise.
        :type return: bool
        """
        if method.upper() not in [
            method.upper() for method in self.allowed_methods
        ]:
            return False
        return True

    def is_authenticated(self, request):
        """
        Method used to check if a client is authenticated. Should be used for
        basic permission checking on a resource wide level. Should not be
        used for obj or field level permissions. This method is called by
        `route` before `self.data` is populated. Designed to be overridden.

        :param request: A Django Http Request object.
        :type request: object

        :return: True if the request is authenticated, false otherwise.
        Defaults to returning true.
        :type return: bool
        """
        return True

    def deserialize(self, action, body):
        """
        Given the request body, runs it through the deserialize method of the
        specified serializer_class and returns a Python native dict object.

        :param action: Not used by default. Can be used to control which
        serializer does the deserializing.

        :param body: The request body. this should be JSON data in string
        format.

        :return: A Python native dictionary representing the received JSON
        data.
        """
        if body:
            return self.serializer.deserialize(body)
        return {}

    def build_filters(self):
        """
        Method that builds a dictionary of filters to apply to the queryset.
        The method makes sure to map the filter to the model attribute
        instead of the schema attribute otherwise we will get an error.

        :return: A dictionary of filters to apply to the queryset. Could be
        empty.

        :type return: dict
        """
        params = self.request.GET
        filter_dict = dict()
        for key, value in params.items():
            field = key.split('__')[0]
            try:
                filter_type = key.split('__')[1]
            except IndexError:
                filter_type = 'exact'
            if field in self.schema:
                field_settings = self.schema.get(field)
                if filter_type in field_settings.get('filters', ()):
                    model_filter = "{field}__{type}".format(
                        field=field_settings.get('attribute'),
                        type=filter_type
                    )
                    filter_dict[model_filter] = value
        return filter_dict

    def apply_filters(self, queryset):
        """
        Method that applies a dictionary of filters to the queryset.

        :param queryset: A Django queryset.
        :type queryset: queryset

        :return: A filtered queryset.
        :type return: queryset
        """
        filters = self.build_filters()
        return queryset.filter(**filters)

    def prepare(self, obj):
        """
        Takes an object instance and turns it into a dict for serialization.

        :param obj: The object to be transformed into a dict.
        :type obj: object

        :return: A dictionary representation of the object.
        :type return: dict
        """
        prepped_obj = dict()
        for key, value in self.schema.items():
            if value.get('readable', True):
                if hasattr(obj, value['attribute']):
                    prepped_obj[key] = getattr(obj, value['attribute'])
        return prepped_obj

    def paginate(self, queryset):
        """
        Method used to paginate list results.

        :param queryset: A Django queryset.
        :type queryset: queryset

        :return: A Page object containing the object list and metadata.
        :type return: object
        """
        page_num = self.request.GET.get('page', 1)
        limit = self.request.GET.get('limit', self.per_page)
        paginator = self.paginator_class(
            object_list=queryset,
            per_page=limit
        )
        try:
            page = paginator.page(number=page_num)
        except InvalidPage:
            return HttpResponse(
                status=ERROR
            )
        return page

    def wrap_list(self, page, object_list):
        """
        Method that wraps a list of objects in a dict for a more concise
        response. Also includes a `meta` key to display pagination
        information.

        If you want to override this method you will need
        to make sure you also override the `list` action method as it
        makes a call to this method to create the response data.

        :param page: A Django Page object.
        :type page: <django.core.paginator.Page>

        :param object_list: A django model queryset.
        :type object_list: queryset

        :return: A dict object containing pagination information and a
        paginated queryset.
        :type return: dict
        """
        return {
            'meta': {
                'page': page.number,
                'count': page.paginator.count,
                'next': page.next_page_number() if page.has_next() else None,
                'previous': page.previous_page_number() if page.has_previous() else None
            },
            'objects': object_list
        }

    def data_is_valid(self):
        for key, value in self.data.items():
            if key in self.schema:
                field = self.schema.get(key)
                validators = field.get('validators', ())
                for validator in validators:
                    if not validator(value):
                        return False
        return True

    def can_create(self, request):
        """
        Object level permissions hook. Should be overridden if you want to
        control who can create new model instances.

        :param request: An Http request object.

        :return: True if the request is allowed to create the new model
        instance, false otherwise.
        """
        return True

    def can_get(self, obj, request):
        """
        Object Level permissions hook for authorizing a request for a single
        model instance. Should be overridden if you want to restrict which
        model instances can be fetched by whom.

        :param obj: The model instance the request is trying to get.

        :param request: The request that wants the object instance.

        :return: True if the request can get the object. False otherwise.
        """
        return True

    def can_get_list(self, object_list, request):
        """
        Object level permissions hook. Use this to control which objects a
        specific request can read. You can pluck objects out of the list, etc.

        :param object_list: List model instances. This list has already been
        run through the filter and the paginator.

        :param request: The request that is trying to get the data.

        :return: True if the request is authorized, false otherwise.
        """
        return True

    def can_update(self, obj, request):
        """
        Object level permissions hook. Use this to restrict which objects can
        be updated and who can update them.

        :param obj: Th model instance the request wants to update.

        :param request: The request that is trying to modify the model instance.

        :return: True if the request is authorized, false otherwise.
        """
        return True

    def can_delete(self, obj, request):
        """
        Object level permissions hook. Use this to determine who can delete
        objects and which objects can be deleted.

        :param obj: The object the request wants to delete.

        :param request: The request that wants to delete the object instance.

        :return: True if the request is authorized, false otherwise.
        """
        return True

    def create_obj(self):
        """
        Method used to create a new model instance.

        This will only populate the new object with values that are declared
        in the schema attribute.

        Note that the method also checks if the model is a user model and calls the
        special `create_user` method instead of the usual `create` method. This is
        so that if a password is provided, it will get hashed correctly. It also
        makes sure that the proper validation is happening when creating a new user.

        :return: A brand new model instance. Fresh out of the oven.
        """
        attributes = dict()
        for key, value in self.data.items():
            if key in self.schema:
                field = self.schema.get(key)
                if field.get('writeable', True):
                    attributes[field['attribute']] = value
        if self.model == get_user_model():
            obj = self.model.objects.create_user(
                **attributes
            )
        else:
            obj = self.model.objects.create(
                **attributes
            )
        return obj

    def get_obj(self, pk):
        """
        Convenience method used to fetch a single model instance from the Db.

        :param pk: The primary key of the object you want to fetch.

        :return: A django model instance or a not found Http response if the
        instance doesn't exist.
        """
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return HttpResponse(status=NOT_FOUND)

    def get_obj_list(self):
        """
        Used to retrieve all model instances for this resource.

        :return: A Django queryset.
        :type return: queryset
        """
        return self.model.objects.all()

    def update_obj(self, obj):
        """
        Method used to update all attributes of a model instance that are
        specified in the schema definition.

        :param obj: The object to updated.

        :return: The updated object instance. By the time this method returns,
        the new data has been committed to the Db.
        :type return: object
        """
        for key, value in self.data.items():
            if key in self.schema:
                schema_field = self.schema.get(key)
                model_field = schema_field.get('attribute')
                setattr(obj, model_field, value)
        obj.save()
        return obj

    def delete_obj(self, obj):
        """
        Convenience method used for deleting an object instance. It doesn't do
        much except delete the object. This is mainly here to be overridden in
        case there are any special operations that need to be done before the
        object is deleted.

        You can also use this method to perform different actions on the object
        besides deleting it, such as simply clearing it to an initial state or
        setting it inactive. Up to you really.

        :param obj: A Django model class instance.

        :return: Returns None if the object was successfully deleted. As long as
        a normal django model instance is provided as the `obj` argument, there
        shouldn't be any major errors.
        """
        obj.delete()
        return None

    def create(self):
        """
        This method creates a new object and returns it's Json representation
        after creation.

        :return: An Http Response object.
        """
        if not self.can_create(self.request):
            return HttpResponse(
                status=FORBIDDEN
            )
        if not self.data_is_valid():
            return HttpResponse(
                status=BAD_REQUEST
            )
        obj = self.create_obj()
        prepped_obj = self.prepare(obj)
        serialized_obj = self.serializer.serialize(prepped_obj)
        return HttpResponse(
            status=CREATED,
            content_type='application/json',
            content=serialized_obj
        )

    def list(self):
        """
        This method puts together a response for GET requests to the list
        endpoint. It also applies any specified filters and paginates the
        list.

        :return: A Django Http Response object.
        :type return: object
        """
        obj_list = self.apply_filters(
            self.get_obj_list()
        )
        if not self.can_get_list(obj_list, self.request):
            return HttpResponse(
                status=FORBIDDEN
            )
        page = self.paginate(obj_list)
        prepped_list = [self.prepare(obj) for obj in page.object_list]
        wrapped_data = self.wrap_list(page, prepped_list)
        serialized_list = self.serializer.serialize(wrapped_data)
        return HttpResponse(
            status=OK,
            content_type='application/json',
            content=serialized_list
        )

    def detail(self, **kwargs):
        """
        This method is used for fetching a single object instance. It gets the
        object from the Db, prepares it, serializes it, and finally returns an
        Http Response object.

        :param kwargs: Optional Keyword Arguments. Should contain the primary
        key for the object instance.
        :type kwargs: dict

        :return: An Http Response object.
        :type return: object
        """
        obj = self.get_obj(pk=kwargs['pk'])
        if not self.can_get(obj, self.request):
            return HttpResponse(
                status=FORBIDDEN
            )
        prepped_obj = self.prepare(obj)
        serialized_obj = self.serializer.serialize(prepped_obj)
        return HttpResponse(
            status=OK,
            content_type='application/json',
            content=serialized_obj
        )

    def update(self, **kwargs):
        """
        This method is used to update a single object instance. It runs the
        request through a convenience method that will update all received
        fields that are present in the resource schema definition.

        :param kwargs: Option arguments. Should contain the object primary key.
        :type kwargs: dict

        :return: A Http response object.
        :type return: object
        """
        obj = self.get_obj(pk=kwargs['pk'])
        if not self.can_update(obj, self.request):
            return HttpResponse(
                status=FORBIDDEN
            )
        if not self.data_is_valid():
            return HttpResponse(
                status=BAD_REQUEST
            )
        obj = self.update_obj(obj)
        prepped_obj = self.prepare(obj)
        serialized_obj = self.serializer.serialize(prepped_obj)
        return HttpResponse(
            status=OK,
            content_type='application/json',
            content=serialized_obj
        )

    def delete(self, **kwargs):
        obj = self.get_obj(pk=kwargs['pk'])
        if not self.can_delete(obj, self.request):
            return HttpResponse(
                status=FORBIDDEN
            )
        self.delete_obj(obj)
        return HttpResponse(
            status=NO_CONTENT
        )
