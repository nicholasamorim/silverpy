#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. module:: api
    :synopsis: A pythonic interface to Silverpop Engage API.

.. moduleauthor:: Nicholas Santos <nicholas@alienretro.com>
"""

import logging
from datetime import datetime

import requests
from lxml import etree


CONTACT_CREATED_FROM_DB = 0
CONTACT_CREATED_MANUALLY = 1
CONTACT_CREATED_OPTED_IN = 2
CONTACT_CREATED_FROM_TRACKING_DB = 3

log = logging.getLogger(__name__)


def pretty_print(doc):
    """Pretty prints the XML object"""
    print(etree.tostring(doc, pretty_print=True))


class API(object):
    """This class manages the access to Silverpop Engage API.

    Usage is as simple as:
    from silverpy import Api

    api = API('user', 'passwd', 'silverpop_url')
    api.login()
    api.add_recipient(...)
    api.logout()
    """
    def __init__(self, username, password, url):
        self._username = username
        self._password = password
        self._url = url

        self._sessionId = None

        self._s = requests.session()

    def _envelope(self, action):
        """Generates the needed envelope XML for every request.
        Every request needs to formatted like this:

        <Envelope>
            <Body>
                <Action/>
            </Body>
        </Envelope>

        :param action: Action to be perfomed.
        :returns: Tuple (root, action_node)
        """

        root = etree.Element('Envelope')
        body = etree.SubElement(root, 'Body')

        action_node = etree.SubElement(body, action)

        return (root, action_node)

    def _check_session(self):
        """Check if user it's already logged in."""
        if not self._sessionId:
            raise StandardError("Authentication is required, please login.")

        return True

    def _parse_from_string(self, response_text):
        """It simply parses the XML from a string."""
        return etree.fromstring(response_text)

    def _create_child_element(self, parent, tag, dict_columns):
        """Given a parent, it will create a sub-tag with
        dict_columns as name/value.
        """
        if not isinstance(parent, etree._Element):
            raise TypeError('parent must be a etree._Element type object.')

        if not isinstance(tag, basestring):
            raise TypeError('tag must be a string.')

        if not isinstance(dict_columns, dict):
            raise TypeError('dict_columns must be a dictionary.')

        for key in dict_columns.iterkeys():
            child = etree.SubElement(parent, tag)
            self._insert_text_node('NAME', key, child)
            self._insert_text_node('VALUE', str(dict_columns[key]), child)

    def _get_session_id(self, response):
        """After login, retrieves SESSIONID from XML
        response and stores it in instance variable _sessionId.
        """
        root = self._parse_from_string(response)
        s = root.xpath('Body/RESULT/SESSIONID')

        if not s:
            msg = 'No SESSIONID in the document.'
            log.error(msg)
            raise ValueError(msg)

        return s[0].text

    def _is_successful(self, response):
        """Proccess XML response.

        :params response: The XML response
        :returns: Tuple (bool_success, error_info)
        """
        error = None

        root = self._parse_from_string(response)
        # Get first element within first element (alwas RESULT)
        result = root.xpath('Body/RESULT/SUCCESS/text()')

        if not result:
            msg = ('Response malformed, '
                   'XPath Expression Body/RESULT/SUCCESS/text() '
                   ' returned nothing')
            log.error(msg)
            raise ValueError(msg)

        # As Silverpop API is rather inconsistent, I need to check whether
        # the result came 'true' or 'success'. Where's the consistency ?
        success = (
            True if result[0].lower() == 'true'
            or result[0].lower() == 'success' else False
        )

        if success is False:
            error_code = root.xpath('Body/Fault/detail/error/errorid')
            error_message = root.xpath('Body/Fault/FaultString')

            if error_message:
                error_message = error_message[0].text
            else:
                msg = (
                    'Response malformed, '
                    'XPath Expression Body/Fault/FaultString returned nothing'
                )
                log.error(msg)
                raise ValueError(msg)

            if error_code:
                error_code = error_code[0].text

            error = (error_code, error_message)

        return (success, error)

    def _request(self, data, auth=True):
        """Execute a request with the given data.

        :param data: The data to be sent in the request.
        :param auth: If True, will check for a estabilished session.
        :returns: Response object.
        """
        url = self._url
        data = etree.tostring(data)

        if auth:
            self._check_session()

        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
        }

        if auth and self._sessionId:
            # API docs states that jsessionid must be appended
            # after a semicolon not a question mark
            url = '%s;jsessionid=%s' % (url, self._sessionId)

        response = self._s.post(url, headers=headers, data=data)
        response.raise_for_status()

        return response

    def _insert_text_node(self, tag, text, target):
        """Inserts a tag and a text node within it on the target.

        :param tag: Tag to be created inside target.
        :param text: Text to be inserted inside the tag.
        :param target: The parent node.
        :returns: The node itself.
        """

        if not isinstance(tag, basestring):
            raise TypeError('tag must be a string.')

        if not isinstance(text, basestring):
            raise TypeError('text must be a string.')

        if not isinstance(target, etree._Element):
            raise TypeError('target must be a etree._Element type object.')

        new_node = etree.SubElement(target, tag)
        new_node.text = text

        return new_node

    def _error(self, error):
        msg = 'Error code %s: %s' % (error[0], error[1])
        log.error(msg)
        raise StandardError(msg)

    def login(self):
        """Log in to Silverpop API.

        :returns: Boolean indicating whether successful or not.
        """

        root, action_node = self._envelope('Login')
        self._insert_text_node('USERNAME', self._username, action_node)
        self._insert_text_node('PASSWORD', self._password, action_node)

        response = self._request(root, auth=False)

        response = response.text
        success, error = self._is_successful(response)

        if error:
            self._error(error)

        if success:
            self._sessionId = self._get_session_id(response)

        return success

    def logout(self):
        """Log off the Silverpop API"""
        root, action_node = self._envelope('Logout')

        response = self._request(root)
        success, error = self._is_successful(response.text)

        if success:
            self._sessionId = None

        return success

    def add_recipient(self, list_id, created_from, columns=None, **kwargs):
        """Add and opt-in a contact to a database.

        :params list_id: The database ID on Silverpop.
        :params created_from: One of the CREATED_FROM_* constants.
        :params columns: A dict containing COLUMN data (including email).
        :returns: A tuple (bool_success, recipient_id, error_tuple).

        """

        root, action_node = self._envelope('AddRecipient')
        self._insert_text_node('LIST_ID', str(list_id), action_node)
        self._insert_text_node('CREATED_FROM', str(created_from), action_node)

        # Simple params that only need a boolean flag
        optional_params_bools = (
            'send_autoreply',
            'update_if_found',
            'allow_html',
        )

        for param in optional_params_bools:
            if param in kwargs and kwargs.get(param) is True:
                self._insert_text_node(param.upper(), 'true', action_node)

        if 'visitor_key' in kwargs:
            self._insert_text_node(
                'VISITOR_KEY', kwargs['visitor_key'], action_node)

        if 'sync_fields' in kwargs:
            if not isinstance(kwargs['sync_fields'], dict):
                raise TypeError('A dict is expected in sync_fields.')

            sync_root = etree.SubElement(action_node, 'SYNC_FIELDS')

            self._create_child_element(
                sync_root,
                'SYNC_FIELD',
                kwargs['sync_fields']
            )

        if columns:
            self._create_child_element(action_node, 'COLUMN', columns)

        response = self._request(root)
        success, error = self._is_successful(response.text)

        response_tree = self._parse_from_string(response.text)
        recipient_id = response_tree.xpath('Body/RESULT/RecipientId//text()')

        if recipient_id:
            recipient_id = recipient_id[0]

        return (success, recipient_id, error)

    def remove_recipient(self, list_id, email, columns=None):
        """Remove a contact of a specified database.

        :params list_id: The database ID on Silverpop.
        :params email: The recipient email.
        :returns: Tuple (bool_success, error_tuple)
        """

        root, action_node = self._envelope('RemoveRecipient')
        self._insert_text_node('LIST_ID', str(list_id), action_node)
        self._insert_text_node('EMAIL', email, action_node)

        if columns:
            self._create_child_element(action_node, 'COLUMN', columns)

        response = self._request(root)
        success, error = self._is_successful(response.text)

        return (success, error)

    def opt_out_recipient(self, list_id, email='', columns=None,
                          mailing_id=None, recipient_id=None, job_id=None):
        """Opt-out a contact. The last three parameters is for Opt-out
        at mailing level.

        :params list_id: Identifies the ID of the database
                         from which to opt out the contact.

        :params email: The contact email address to opt out.
        :params columns: Optional dict defining optional <COLUMN> tags.
        :params mailing_id: Supply this if you don't supply an email.
        :params recipient_id: Supply this if you don't supply an email.
        :params job_id_id: Supply this if you don't supply an email.
        :returns: Tuple (bool_success, error_tuple)
        """
        root, action_node = self._envelope('OptOutRecipient')

        self._insert_text_node('LIST_ID', str(list_id), action_node)

        if email:
            self._insert_text_node('EMAIL', email, action_node)
        else:
            if mailing_id and recipient_id and job_id:
                # If no email is supplied, three params are required:
                # 'mailing_id', 'recipient_id' and 'job_id'
                self._insert_text_node(
                    'MAILING_ID',
                    str(mailing_id),
                    action_node
                )

                self._insert_text_node(
                    'RECIPIENT_ID',
                    str(recipient_id), action_node
                )

                self._insert_text_node(
                    'JOB_ID',
                    str(job_id),
                    action_node
                )
            else:
                raise ValueError(
                    "If you don't supply email, "
                    "you need to supply mailing_id, recipient_id and job_id"
                )

        if columns:
            self._create_child_element(action_node, 'COLUMN', columns)

        response = self._request(root)
        success, error = self._is_successful(response.text)

        return (success, error)

    def create_contact_list(self, database_id, contact_list_name,
                            visibility=0):
        """Creates a new contact list in Silverpop.

        :params database_id: The Id of the database the new Contact List
                             will be associated with.
        :params contact_list_name: The name of the Contact List to be created.
        :params visibility: Defines the visibility of the Contact List being
                            created.
                            0 - Private, 1 - Shared
        :returns: A tuple (bool_success, contact_list_id, error_info)
        """
        root, action_node = self._envelope('CreateContactList')

        self._insert_text_node('DATABASE_ID', str(database_id), action_node)
        self._insert_text_node(
            'CONTACT_LIST_NAME',
            contact_list_name,
            action_node
        )
        self._insert_text_node('VISIBILITY', str(visibility), action_node)

        response = self._request(root)
        success, error = self._is_successful(response.text)
        contact_list_id = None

        if success:
            response_tree = self._parse_from_string(response.text)
            contact_list_id = response_tree.xpath(
                'Body/RESULT/CONTACT_LIST_ID//text()'
            )
            if contact_list_id:
                contact_list_id = contact_list_id[0]

        return (success, contact_list_id, error)

    def add_contact_to_contact_list(self, contact_list_id, contact_id='',
                                    columns=None):
        """This interface adds one new contact to a Contact List. If you want
        to add a contact using its email, you must pass it as an 'email' key
        in columns param.

        :params contact_list_id: The ID of the Contact List to which
                                 you are adding the contact.
        :params contact_id: The ID of the contact being added to the Contact
                            List. Either a CONTACT_ID or COLUMN elements must
                            be provided. If CONTACT_ID is provided, any COLUMN
                            elements will be ignored.
        :params colums: A dictionary is expected here to feed the COLUMN
                        fields.
        :returns: A tuple (bool_success, error_info)
        """
        root, action_node = self._envelope('AddContactToContactList')

        self._insert_text_node(
            'CONTACT_LIST_ID',
            str(contact_list_id),
            action_node
        )

        if contact_id:
            self._insert_text_node('CONTACT_ID', str(contact_id), action_node)

        if not contact_id and columns:
            self._create_child_element(action_node, 'COLUMN', columns)

        response = self._request(root)
        success, error = self._is_successful(response.text)

        return (success, error)

    def send_mailing(self, mailing_id, recipient_email, columns=None):
        """Sends mailing to the specified ID.

        :params mailing_id: Identifies the mailing Engage will send.
        :params recipient_email: Identifies the targeted
                                 contact's email address.

        :params: columns: Optional dict defining optional <COLUMN> tags.
        :returns: Tuple (bool_success, error_tuple)
        """
        root, action_node = self._envelope('SendMailing')

        self._insert_text_node('MailingId', str(mailing_id), action_node)
        self._insert_text_node('RecipientEmail', recipient_email, action_node)

        if columns:
            self._create_child_element(action_node, 'COLUMN', columns)

        response = self._request(root)
        success, error = self._is_successful(response.text)

        return (success, error)

    def schedule_mailing(self, template_id, list_id, mailing_name,
                         visibility=1, substitutions=None,
                         scheduled=None, **kwargs):
        """Sends a template-based mailing to a specific database or query.

        :params template_id: ID of template upon which to base the mailing.
        :params list_id: ID of database, query, or contact list
                         to send the template-based mailing.

        :params mailing_name: Name to assign to the generated mailing.
        :params visibility: Where to save. Values are
                            0 - Private folder, 1 - Shared folder.

        :params substitutions: A dict defining template substitution
                               names and values.

        :params scheduled: Datetime obj specifying the date and time
                           the mailing will be scheduled.

        :params kwargs: Optional parameters. Check API documentation
                        for more info.

        :returns: Tuple (bool_success, mailing_id)
        """
        root, action_node = self._envelope('ScheduleMailing')

        self._insert_text_node('TEMPLATE_ID', str(template_id), action_node)
        self._insert_text_node('LIST_ID', str(list_id), action_node)
        self._insert_text_node('MAILING_NAME', mailing_name, action_node)
        self._insert_text_node('VISIBILITY', str(visibility), action_node)

        # Simple params that only need a boolean flag
        optional_params_bools = (
            'send_html',
            'send_aol',
            'send_text',
            'inbox_monitor',
            'create_parent_folder',
        )

        for param in optional_params_bools:
            if param in kwargs and kwargs.get(param) is True:
                self._insert_text_node(param.upper(), 'true', action_node)

        # Simple params that its key/value it's all that is needed
        optional_params = (
            'subject',
            'from_name',
            'from_address',
            'reply_to',
            'parent_folder_path',
        )

        for param in optional_params:
            if param in kwargs and kwargs.get(param):
                self._insert_text_node(
                    param.upper(),
                    kwargs[param],
                    action_node
                )

        if 'send_time_optimization' in kwargs:
            sto = kwargs['send_time_optimization']
            if sto not in ('NONE', 'SEND_24HRS', 'SEND_WEEK'):
                raise ValueError(
                    'send_time_optimization must be '
                    'NONE, SEND_24HRS or SEND_WEEK'
                )
            self._insert_text_node('SEND_TIME_OPTIMIZATION', sto, action_node)

        if 'supression_list' in kwargs:
            sl = kwargs['supression_list']
            if not isinstance(sl, list):
                raise TypeError('supression_list must be a list')
            sl_node = etree.SubElement(action_node, 'SUPRESSION_LISTS')

            for elt in sl:
                self._insert_text_node('SUPRESSION_LIST_ID', str(elt), sl_node)

        # If present, will schedule mailing. If not, will be sent immediatelly.
        if scheduled:
            if not isinstance(scheduled, datetime):
                raise TypeError('scheduled param must be a datetime object.')

            scheduled = scheduled.strftime('%m-%d-%Y %H:%M:%S %p')
            self._insert_text_node('SCHEDULED', scheduled, action_node)

        # This is used to perform template substitution like %%CustomerID%%
        if substitutions:
            if not isinstance(substitutions, dict):
                raise TypeError('substitutions param must be a dict!')

            subs_node = etree.SubElement(action_node, 'SUBSTITUTIONS')
            self._create_child_element(
                subs_node, 'SUBSTITUTION', substitutions
            )

        response = self._request(root)
        success, error = self._is_successful(response.text)

        if error:
            self._error(error)

        response_tree = self._parse_from_string(response.text)
        mailing_id = response_tree.xpath('Body/RESULT/MAILING_ID//text()')

        if mailing_id:
            mailing_id = mailing_id[0]

        return (success, mailing_id)
