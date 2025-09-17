# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################
import babel.dates
import pytz
import logging
import odoo
from odoo import models, api
from odoo.osv import expression
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import posix_to_ldml, pycompat, DATE_LENGTH, file_open
from odoo import http
from odoo.http import request
import werkzeug
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi
from odoo.addons.web.controllers.main import WebClient

_logger = logging.getLogger(__name__)


def format_date(env, value, lang_code=False, date_format=False):
    if not value:
        return ''
    if isinstance(value, str):
        if len(value) < DATE_LENGTH:
            return ''
        if len(value) > DATE_LENGTH:
            # a datetime, convert to correct timezone
            value = odoo.fields.Datetime.from_string(value)
            value = odoo.fields.Datetime.context_timestamp(env['res.lang'], value)
        else:
            value = odoo.fields.Datetime.from_string(value)

    lang = env['res.lang']._lang_get(lang_code or env.context.get('lang') or 'en_US')
    locale = babel.Locale.parse(lang.code)
    locale=str(locale)
    if locale.lower().startswith('ar'):
        locale = "ar"
    if not date_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)

    return babel.dates.format_date(value, format=date_format, locale=locale)


odoo.tools.misc.format_date = format_date


class WebClientIhnerit(WebClient):
    @http.route('/web/webclient/locale/<string:lang>', type='http', auth="none")
    def load_locale(self, lang):
        magic_file_finding = [lang.replace("_", '-').lower(), lang.split('_')[0]]
        for code in magic_file_finding:
            if code.lower().startswith('ar'):
                code = 'ar-sa'
            try:
                return http.Response(
                    werkzeug.wsgi.wrap_file(
                        request.httprequest.environ,
                        file_open('web/static/lib/moment/locale/%s.js' % code, 'rb')
                    ),
                    content_type='application/javascript; charset=utf-8',
                    headers=[('Cache-Control', 'max-age=36000')],
                    direct_passthrough=True,
                )
            except IOError:
                _logger.debug("No moment locale for code %s", code)

        return request.make_response("", headers=[
            ('Content-Type', 'application/javascript'),
            ('Cache-Control', 'max-age=36000'),
        ])


class except_orm(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)


class BaseModelExtend(models.BaseModel):
    _name = 'basemodel.extend_custom_months'

    def _register_hook(self):

        @api.model
        def _read_group_format_result(self, data, annotated_groupbys, groupby, domain):
            """
                Helper method to format the data contained in the dictionary data by 
                adding the domain corresponding to its values, the groupbys in the 
                context and by properly formatting the date/datetime values.

            :param data: a single group
            :param annotated_groupbys: expanded grouping metainformation
            :param groupby: original grouping metainformation
            :param domain: original domain for read_group
            """
            sections = []
            for gb in annotated_groupbys:
                ftype = gb['type']
                value = data[gb['groupby']]

                # full domain for this groupby spec
                d = None
                if value:
                    if ftype == 'many2one':
                        value = value[0]
                    elif ftype in ('date', 'datetime'):
                        locale = self._context.get('lang') or 'en_US'
                        # use arabic instade of arabic syria
                        if locale.lower().startswith('ar'):
                            locale = "ar"
                        fmt = DEFAULT_SERVER_DATETIME_FORMAT if ftype == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                        tzinfo = None
                        range_start = value
                        range_end = value + gb['interval']
                        # value from postgres is in local tz (so range is
                        # considered in local tz e.g. "day" is [00:00, 00:00[
                        # local rather than UTC which could be [11:00, 11:00]
                        # local) but domain and raw value should be in UTC
                        if gb['tz_convert']:
                            tzinfo = range_start.tzinfo
                            range_start = range_start.astimezone(pytz.utc)
                            range_end = range_end.astimezone(pytz.utc)

                        range_start = range_start.strftime(fmt)
                        range_end = range_end.strftime(fmt)
                        if ftype == 'datetime':
                            label = babel.dates.format_datetime(
                                value, format=gb['display_format'],
                                tzinfo=tzinfo, locale=locale
                            )
                        else:
                            label = babel.dates.format_date(
                                value, format=gb['display_format'],
                                locale=locale
                            )
                        data[gb['groupby']] = ('%s/%s' % (range_start, range_end), label)
                        d = [
                            '&',
                            (gb['field'], '>=', range_start),
                            (gb['field'], '<', range_end),
                        ]

                if d is None:
                    d = [(gb['field'], '=', value)]
                sections.append(d)
            sections.append(domain)

            data['__domain'] = expression.AND(sections)
            if len(groupby) - len(annotated_groupbys) >= 1:
                data['__context'] = {'group_by': groupby[len(annotated_groupbys):]}
            del data['id']
            return data

        # -------------------------------------------------------
        models.BaseModel._read_group_format_result = _read_group_format_result
        return super(BaseModelExtend, self)._register_hook()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
