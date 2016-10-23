=============
Django RestUp
=============
**DO NOT USE IN PRODUCTION!!!**
This package is in very early alpha and has no tests! It is currently more of 
a proof of concept.

Philosophy
----------
Django RestUp takes time-tested ideas from other Django REST API packages such 
as Django REST Framework, Django Tastypie, and Restless.

It expands upon these ideas by applying a bit more flexibility/extensibility and
explicitness. There is a trade-off. RestUp requires a bit more configuration than
other packages/libraries.

The main difference between RestUp and other packages is how RestUp determines API
data structure. RestUp requires the developer to explicitly declare the structure of
their data on a per-resource basis.

This explicitness comes with some major benefits:

- An extra layer of security and sanity checking for your data.
- Makes it easy to see the structure of your data and make changes to that 
  structure without side effects.
- Expose only the data you want to expose, and in the manner that you want 
  to expose it.
- Allows for deep authentication and authorization on a per-resource, 
  per-object, and even per-field basis.

===============
Getting Started
===============
Schema Definition
-----------------
At the core of a RestUp ``ModelResource`` is it's schema definition. You 
define a schema as a native python dictionary object. This schema is used to 
populate the JSON response for ``GET`` requests. It is also used to help 
deserialize ``POST`` ed data into native python data types so it can be used to 
create a new object or modify an existing one.

**Example:**
Assume we have a Django model with the following structure::

    # In ~/yourapp/models.py
    from django.db import models
    
    
    class Book(models.Model):
    
        title = models.CharField(
            max_lenfth=200,
            blank=False
        )
        
        isbn = models.CharField(
            max_length=100,
            blank=False
        )
        
        favorites = models.PositiveIntegerField(
            blank=True,
            default=0
        )
        
        secret_field = models.CharField(
            max_length=20,
            blank=False
        )

Let's define a RestUp ``ModelResource`` class to expose this resource::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites'
            },
            'secret_field': {
                'attribute': 'secret_field'
            }
        }

You'll also need to tell Django where to find the urls for this resource::

    # In ~/yourproject/urls.py
    
    # ~~? (other imports)
    from django.conf.urls import include
    from yourapp.api import BookResource
    
    urlpatterns = [
        # ...?
        url(
            r'^api/books/', include(BookResource.urls())
        )
    ]

That's all you need to define in order to make any ``GET, POST, PUT, DELETE`` 
requests to the endpoint. 

Permissions
-----------
However, right now, we're letting just anyone mess with our data! There's 
no security at all! We only want logged in users to be able to manipulate 
the data. We'll allow anyone to ``GET`` it though::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites'
            },
            'secret_field': {
                'attribute': 'secret_field'
            }
        }
        
        def is_authenticated(self, request):  # Add this method override
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()

You can put anything you want in the ``is_authenticated`` method as long as it 
returns true for authenticated requests and false for unauthorized requests. You'll
notice that you have access to the request object. This is a normal Django request
object. You can do anything with it that you could do in a normal Django view class.
The ``is_authenticated`` method is the second permission hook to be called in any
request. It is called right after the allowed methods check and right before the
request is routed to the correct action handler. Speaking of the Allowed methods
check, we don't want anyone to be able to delete our models. Let's stop them 
from doing that::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites'
            },
            'secret_field': {
                'attribute': 'secret_field'
            }
        }
        
        def is_authenticated(self, request):
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()
            
        def can_delete(self, obj, request):  # Override this method
            return False

There we go! Now all ``DELETE`` requests to any of the ``BookResource`` endpoints
will return a ``403 Forbidden`` HTTP response. What about the ``secret_field``
field? Surely we don't want everyone to see that? But, we need to populate it with
data from the client. This is where RestUp becomes something special::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites'
            },
            'secret_field': {
                'attribute': 'secret_field',
                'readable': False  # Add this line
            }
        }
        
        def is_authenticated(self, request):
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()
            
        def can_delete(self, obj, request):
            return False

All we need to do is add a ``'readable'`` key to our field declaration inside
our schema and set it's value to ``False``. This will ensure that this data is
not sent out to any requesting client. However, we can still apply ``POST`` ed
data to this field.

Object level permissions
------------------------
We only want staff users to be able to create and update any ``Book`` objects. 
Let's make sure no one else can::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites'
            },
            'secret_field': {
                'attribute': 'secret_field',
                'readable': False
            }
        }
        
        def is_authenticated(self, request):
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()
            
        def can_create(self, request):  # Override this method
            return request.user.is_staff
            
        def can_delete(self, obj, request):
            return False
            
        def can_update(self, obj, request):  # Override this method
            return request.user.is_staff

There we go! Now only staff members can create and update ``Book`` resources!

We now have a fairly robust RESTful resource. Our resource allows us to
create, update, list, and get ``Book`` objects. We also make sure non staff users
can't do anything but ``GET`` the resource from either it's list or detail endpoints.

Filtering
---------
We want users to be able to filter ``Book`` objects. We'll allow them to 
filter the results based on the favorites field::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites',
                'filters': (  # Add this key
                    'gt', 'lt',
                )
            },
            'secret_field': {
                'attribute': 'secret_field',
                'readable': False
            }
        }
        
        def is_authenticated(self, request):
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()
            
        def can_create(self, request):
            return request.user.is_staff
            
        def can_delete(self, obj, request):
            return False
            
        def can_update(self, obj, request):
            return request.user.is_staff

Great! Now, if our users want to get a list of books with more than 10 favorites
they only need to send a request to ``http://mysite.com/api/books/?favorites__gt=10``.
You can use any of the standard Django query filters defined 
`in the Django docs <https://docs.djangoproject.com/en/1.10/ref/models/querysets/#field-lookups>`_

Validation
----------
We want to be sure that the client is only providing a positive integer to our 
favorites field. We will create 2 validator functions to make sure the value
is correct::

    # In ~/yourapp/api.py
    from restup import ModelResource
    from .models import Book
    
    # We will add two methods for illustrative purposes, but this check could
    # easily be done with a single function.
    
    def is_integer(value):  # Add this method
        return type(value) == int
        
    def is_positive(value):  # Add this method
        return value > 0
    
    
    class BookResource(ModelResource):
    
        model = Book
        
        schema = {
            'title': {
                'attribute': 'title'
            },
            'isbn': {
                'attribute': 'isbn'
            },
            'favorites': {
                'attribute': 'favorites',
                'filters': (
                    'gt', 'lt',
                ),
                'validators': (  # Add this key
                    is_integer,
                    is_positive
                )
            },
            'secret_field': {
                'attribute': 'secret_field',
                'readable': False
            }
        }
        
        def is_authenticated(self, request):
            if request.method in self.SAFE_METHODS:
                return True
            return request.user.is_authenticated()
            
        def can_create(self, request):
            return request.user.is_staff
            
        def can_delete(self, obj, request):
            return False
            
        def can_update(self, obj, request):
            return request.user.is_staff

Validator functions should take a single argument. This argument should be
the ``value`` of the key in the received data. The function should return
``True`` if the value is valid and ``False`` otherwise. A check like the 
one in our example isn't srictly necessary as Django's model backend
would throw an exception if we tried to save anything that wasn't a positive
integer. However, that would return a ``500 Server error`` response. That's not
very helpful for the client. It would be much better to return a ``400 Bad Request``
response to let the client know they entered something incorrectly.

==========
Conclusion
==========
Well, that's a basic rundown of how it all works. If you want a more in-depth 
understanding, please take a look at the source code. The ``ModelResource``
class is a great place to start. 

Documentation
-------------
As the project develops, I plan on adding 
more complete documentation including:

- An in-depth tutorial
- Full API reference
- In-depth explanation of data flow

Upcoming required development
-----------------------------
- Tests!
- Robust handling for edge-cases.

Upcoming Features
-----------------
A list of some features on the docket:

- Support for custom per-field pre and post processing functions. These 
  will take a value returned by the database or from client ``POST`` ed data 
  and perform any necessary complex transformations.
- Support for custom per-field authorization functions for extremely granular
  permissions control.
- Self documenting schema endpoints similar to those of Django REST Framework.
- Return resource URIs in JSON data.
- Custom URL namespaces.
  
Features I won't add
--------------------
- XML/YAML/etc support. I don't use these often and they aren't very easy to 
  serialize. If someone else wants to add support, they are welcome to create
  a pull request.
- Python 2 support. Sorry, but it's time to move on.
- Django < 1.8 support. See above.

============
Contributing
============
This project is in very early development. It should only be used on non-production
projects until it reaches ``V1.0.0``.

Any criticisms or ideas welcome. Just open up an issue.

If you want to contribute to the source code, it is preferred that you open an issue
before submitting a pull request to discuss the changes or enhancements you want to
make. I will not discriminate against anyone for any reason.

