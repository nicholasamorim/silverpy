silverpy
========

An easy-to-use Silverpop Engage Library. It only supports some features for now, but they have been tested and tried on production environemnt.

Usage
=====

Usage is as simple as:

```
from silverpy import Api

api = Api('user', 'passwd', 'silverpop_url')
api.login()
api.add_recipient(...)
api.logout()
```


