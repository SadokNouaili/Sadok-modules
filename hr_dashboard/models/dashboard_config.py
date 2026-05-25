# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


def _safe(fn, default, label=None):
    """Run fn() and return default if anything fails — log the error."""
    try:
        return fn()
    except Exception as e:
        if label:
            _logger.warning("hr_dashboard: section '%s' failed: %s", label, e)
        else:
            _logger.warning("hr_dashboard: section failed: %s", e)
        return default


class HRDashboardConfig(models.Model):
    _name = 'hr.dashboard.config'
    _description = 'HR Dashboard Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Configuration Name', default='Default', required=True)
    active = fields.Boolean(default=True)

    # Logo & branding
    logo = fields.Binary(string='Dashboard Logo', attachment=True)
    logo_filename = fields.Char(string='Logo Filename')
    show_logo = fields.Boolean(string='Show Logo', default=True)
    dashboard_title = fields.Char(string='Dashboard Title', default='HR Analytics')
    dashboard_subtitle = fields.Char(string='Subtitle', default='Human Resources Overview')

    # Theme colors — Earthy harvest palette
    primary_color = fields.Char(string='Primary Color', default='#606C38')      # Olive Leaf
    secondary_color = fields.Char(string='Secondary Color', default='#BC6C25')  # Copper
    accent_color = fields.Char(string='Accent Color', default='#DDA15E')        # Light Caramel

    bg_gradient_start = fields.Char(string='Background Gradient Start', default='#FEFAE0')  # Cornsilk
    bg_gradient_mid = fields.Char(string='Background Gradient Middle', default='#F5EFC9')
    bg_gradient_end = fields.Char(string='Background Gradient End', default='#E9D9A8')

    card_color_1 = fields.Char(string='Card Color 1 (Employees)', default='#606C38')   # Olive
    card_color_2 = fields.Char(string='Card Color 2 (Attendance)', default='#283618')  # Black Forest
    card_color_3 = fields.Char(string='Card Color 3 (Leaves)', default='#DDA15E')      # Light Caramel
    card_color_4 = fields.Char(string='Card Color 4 (Payroll)', default='#BC6C25')     # Copper
    card_color_5 = fields.Char(string='Card Color 5 (Expenses)', default='#A0522D')    # Sienna
    card_color_6 = fields.Char(string='Card Color 6 (Contracts)', default='#8B7355')   # Walnut

    text_color = fields.Char(string='Text Color', default='#283618')         # Black Forest
    text_muted_color = fields.Char(string='Muted Text Color', default='#606C38')  # Olive Leaf

    glass_opacity = fields.Float(string='Glass Opacity', default=0.55)
    blur_intensity = fields.Integer(string='Blur Intensity (px)', default=18)
    border_radius = fields.Integer(string='Border Radius (px)', default=18)
    enable_animations = fields.Boolean(string='Enable Animations', default=True)

    @api.model
    def get_active_config(self):
        """Return active config or create a default one."""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            config = self.create({'name': 'Default'})
        return config

    # -------- helpers --------
    def _has_model(self, model_name):
        return model_name in self.env

    def _has_field(self, model_name, field_name):
        try:
            return field_name in self.env[model_name]._fields
        except Exception:
            return False

    def _safe_count(self, model_name, domain, label=None):
        if not self._has_model(model_name):
            return 0
        try:
            return self.env[model_name].sudo().search_count(domain)
        except Exception as e:
            _logger.warning("hr_dashboard: count on %s failed (%s): %s", model_name, label or domain, e)
            return 0

    # -------- main data endpoint --------
    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        """Aggregate HR data for the dashboard.

        Every section is wrapped to never raise — a missing field, missing model,
        or unknown state value returns zero/empty rather than killing the response.
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')

        today = fields.Date.today()

        # ============ KPI cards ============
        total_employees = self._safe_count('hr.employee', [('active', '=', True)], 'total_employees')

        new_hires = self._safe_count('hr.employee', [
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to + ' 23:59:59'),
        ], 'new_hires')

        present_today = self._safe_count('hr.attendance', [
            ('check_in', '>=', f'{today} 00:00:00'),
            ('check_in', '<=', f'{today} 23:59:59'),
        ], 'present_today')

        # ============ Leaves ============
        # Pending = waiting approval (confirm = first level, validate1 = second level)
        # Approved = state='validate' (finalized leaves)
        pending_leaves = self._safe_count('hr.leave', [('state', 'in', ('confirm', 'validate1'))], 'pending_leaves')
        approved_leaves = self._safe_count('hr.leave', [
            ('state', '=', 'validate'),
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
        ], 'approved_leaves')
        # Total approved (no date filter, for the KPI subtitle)
        total_approved_leaves = self._safe_count('hr.leave', [('state', '=', 'validate')], 'total_approved_leaves')

        # ============ Expenses ============
        # Odoo 19 hr.expense states: draft → submitted → approved → posted → in_payment → paid
        # In some installs the 'submitted' state is bypassed entirely (auto-approve flow),
        # so 'Pending' here means "expenses still needing review" = draft OR submitted.
        # This matches what a manager would want to see at a glance.
        pending_expenses = self._safe_count(
            'hr.expense', [('state', 'in', ('draft', 'submitted'))], 'pending_expenses'
        )
        draft_expenses = self._safe_count('hr.expense', [('state', '=', 'draft')], 'draft_expenses')
        submitted_expenses = self._safe_count('hr.expense', [('state', '=', 'submitted')], 'submitted_expenses')
        approved_expenses = self._safe_count('hr.expense', [('state', '=', 'approved')], 'approved_expenses')

        # Expense total — sum the numeric amount field that exists
        expense_total = 0.0
        if self._has_model('hr.expense'):
            amount_field = None
            for cand in ('total_amount', 'total_amount_currency', 'untaxed_amount', 'price_total', 'amount_total'):
                if self._has_field('hr.expense', cand):
                    amount_field = cand
                    break
            if amount_field:
                expense_total = _safe(lambda: sum(
                    self.env['hr.expense'].sudo().search([
                        ('date', '>=', date_from), ('date', '<=', date_to),
                    ]).mapped(amount_field)
                ), 0.0, 'expense_total')

        # ============ Payslips (Odoo 19 Enterprise) ============
        # Odoo 19 hr.payslip states: 'draft' / 'validated' / 'paid' / 'cancel'
        # (Older Odoo used 'verify' / 'done' but Odoo 19 renamed these.)
        #
        # Date filtering: a payslip with period [date_from, date_to] OVERLAPS the dashboard
        # range [range_from, range_to] when date_from <= range_to AND date_to >= range_from.
        # This catches payslips like "May 1 → May 31" when the dashboard range is the
        # last 30 days (e.g. Apr 25 → May 25), which strict containment would miss.
        payslip_count = 0
        payslip_total = 0.0
        payslip_draft = 0
        payslip_done = 0
        if self._has_model('hr.payslip'):
            overlap_domain = [
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ]
            payslip_count = self._safe_count('hr.payslip', overlap_domain, 'payslip_count')
            payslip_draft = self._safe_count('hr.payslip',
                overlap_domain + [('state', 'in', ('draft', 'verify'))],
                'payslip_draft')
            payslip_done = self._safe_count('hr.payslip',
                overlap_domain + [('state', 'in', ('validated', 'paid', 'done'))],
                'payslip_done')
            # Sum net wage if the field exists
            if self._has_field('hr.payslip', 'net_wage'):
                payslip_total = _safe(lambda: sum(
                    self.env['hr.payslip'].sudo().search(overlap_domain).mapped('net_wage')
                ), 0.0, 'payslip_total')

        # Active versions (Odoo 19): hr.version replaced hr.contract
        active_contracts = 0
        if self._has_model('hr.version'):
            def _count_versions():
                Version = self.env['hr.version'].sudo()
                if 'employee_id' in Version._fields:
                    domain = [('employee_id.active', '=', True)] if 'active' in self.env['hr.employee']._fields else []
                    versions = Version.search(domain)
                    return len(set(versions.mapped('employee_id').ids))
                return Version.search_count([])
            active_contracts = _safe(_count_versions, total_employees, 'active_contracts')
        else:
            active_contracts = total_employees

        # ============ Charts ============
        # Departments
        def _dept_data():
            if not self._has_model('hr.department'):
                return []
            departments = self.env['hr.department'].sudo().search([])
            data = []
            for dept in departments:
                count = self._safe_count('hr.employee', [
                    ('department_id', '=', dept.id), ('active', '=', True),
                ])
                if count:
                    data.append({'name': dept.name or '-', 'count': count})
            data.sort(key=lambda x: x['count'], reverse=True)
            return data[:8]
        dept_data = _safe(_dept_data, [], 'dept_data')

        # Leaves by type
        def _leave_data():
            if not self._has_model('hr.leave.type') or not self._has_model('hr.leave'):
                return []
            types = self.env['hr.leave.type'].sudo().search([])
            data = []
            for lt in types:
                count = self._safe_count('hr.leave', [
                    ('holiday_status_id', '=', lt.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', date_from),
                    ('date_to', '<=', date_to),
                ])
                if count:
                    data.append({'name': lt.name or '-', 'count': count})
            return data
        leave_data = _safe(_leave_data, [], 'leave_data')

        # Attendance trend (last 14 days)
        def _attendance_trend():
            if not self._has_model('hr.attendance'):
                return []
            trend = []
            for i in range(13, -1, -1):
                day = today - timedelta(days=i)
                count = self._safe_count('hr.attendance', [
                    ('check_in', '>=', f'{day} 00:00:00'),
                    ('check_in', '<=', f'{day} 23:59:59'),
                ])
                trend.append({'date': day.strftime('%b %d'), 'count': count})
            return trend
        attendance_trend = _safe(_attendance_trend, [], 'attendance_trend')

        # Employee growth (last 6 months)
        def _growth():
            data = []
            for i in range(5, -1, -1):
                ref_date = today - timedelta(days=i * 30)
                count = self._safe_count('hr.employee', [
                    ('create_date', '<=', f'{ref_date} 23:59:59'),
                    ('active', '=', True),
                ])
                data.append({'month': ref_date.strftime('%b %Y'), 'count': count})
            return data
        growth_data = _safe(_growth, [], 'growth_data')

        # Gender distribution — Odoo 19 hr.employee field is 'sex'
        # (renamed from 'gender' in earlier versions; tooltip says "legal sex recognized by the state").
        # Selection: [('male','Male'),('female','Female'),('other','Other')].
        # We try 'sex' first (Odoo 19), then 'gender' (legacy) for backward compatibility.
        def _gender_distribution():
            Employee = self.env['hr.employee']
            gender_field = None
            for cand in ('sex', 'gender'):
                if cand in Employee._fields:
                    gender_field = cand
                    break
            if not gender_field:
                return {'male': 0, 'female': 0, 'other': 0, 'extra': []}

            # Read the selection options actually defined on the field
            try:
                sel = dict(Employee._fields[gender_field]._description_selection(self.env))
            except Exception:
                sel = {'male': 'Male', 'female': 'Female', 'other': 'Other'}

            counts = {'male': 0, 'female': 0, 'other': 0}
            extra = []  # for any non-standard values found

            for code, label in sel.items():
                cnt = self._safe_count(
                    'hr.employee',
                    [(gender_field, '=', code), ('active', '=', True)],
                    f'gender[{code}]',
                )
                lc = (code or '').lower()
                if lc in ('male', 'm'):
                    counts['male'] += cnt
                elif lc in ('female', 'f'):
                    counts['female'] += cnt
                elif lc in ('other', 'o'):
                    counts['other'] += cnt
                else:
                    # Anything else (e.g. 'unspecified', custom codes) goes into 'other'
                    counts['other'] += cnt
                    if cnt:
                        extra.append({'code': code, 'label': label, 'count': cnt})

            # Also count records where the field is empty/null — bucket into 'other'
            try:
                empty_cnt = self._safe_count(
                    'hr.employee',
                    [(gender_field, '=', False), ('active', '=', True)],
                    'gender[empty]',
                )
                counts['other'] += empty_cnt
            except Exception:
                pass

            counts['extra'] = extra
            counts['field_name'] = gender_field
            return counts

        gender_dist = _gender_distribution()
        male = gender_dist.get('male', 0)
        female = gender_dist.get('female', 0)
        other = gender_dist.get('other', 0)

        # Expenses by category - use _read_group (Odoo 17+ API), fall back to legacy
        def _expenses_by_cat():
            if not self._has_model('hr.expense'):
                return []
            Expense = self.env['hr.expense'].sudo()
            if not self._has_field('hr.expense', 'product_id'):
                return []
            amount_field = None
            for cand in ('total_amount', 'total_amount_currency', 'untaxed_amount', 'price_total', 'amount_total'):
                if self._has_field('hr.expense', cand):
                    amount_field = cand
                    break
            if not amount_field:
                return []
            domain = [('date', '>=', date_from), ('date', '<=', date_to)]
            try:
                rows = Expense._read_group(
                    domain=domain,
                    groupby=['product_id'],
                    aggregates=[f'{amount_field}:sum'],
                )
                result = []
                for product, amt in rows:
                    name = product.display_name if product else 'Other'
                    result.append({'name': name, 'amount': amt or 0.0})
                return result[:6]
            except Exception:
                rows = Expense.read_group(
                    domain=domain,
                    fields=['product_id', f'{amount_field}:sum'],
                    groupby=['product_id'],
                )
                result = []
                for g in rows:
                    pid = g.get('product_id')
                    name = pid[1] if pid else 'Other'
                    result.append({'name': name, 'amount': g.get(amount_field, 0.0) or 0.0})
                return result[:6]
        expense_by_cat = _safe(_expenses_by_cat, [], 'expense_by_cat')

        # Sparklines
        sparkline_employees = [g['count'] for g in growth_data] if growth_data else [0]
        sparkline_attendance = [a['count'] for a in attendance_trend][-7:] if attendance_trend else [0]

        # Appraisal data (Odoo 19 Enterprise)
        appraisal_data = self._get_appraisal_data(date_from, date_to, limit=10)

        return {
            'kpis': {
                'total_employees': total_employees,
                'new_hires': new_hires,
                'present_today': present_today,
                'pending_leaves': pending_leaves,
                'approved_leaves': approved_leaves,
                'total_approved_leaves': total_approved_leaves,
                'pending_expenses': pending_expenses,
                'draft_expenses': draft_expenses,
                'submitted_expenses': submitted_expenses,
                'approved_expenses': approved_expenses,
                'expense_total': round(expense_total or 0.0, 2),
                'active_contracts': active_contracts,
                'pending_appraisals': appraisal_data.get('pending_count', 0),
                'done_appraisals': appraisal_data.get('done_count', 0),
                'upcoming_appraisals': appraisal_data.get('upcoming_count', 0),
                'payslip_count': payslip_count,
                'payslip_draft': payslip_draft,
                'payslip_done': payslip_done,
                'payslip_total': round(payslip_total or 0.0, 2),
            },
            'has_payroll_module': 'hr.payslip' in self.env,
            'charts': {
                'departments': dept_data,
                'leaves': leave_data,
                'attendance_trend': attendance_trend,
                'growth': growth_data,
                'gender': {'male': male, 'female': female, 'other': other},
                'expenses_by_category': expense_by_cat,
                'appraisals_by_state': appraisal_data.get('by_state', []),
            },
            'sparklines': {
                'employees': sparkline_employees,
                'attendance': sparkline_attendance,
            },
            'has_appraisal_module': 'hr.appraisal' in self.env,
            'date_from': date_from,
            'date_to': date_to,
        }

    # ============ Employee Spotlight ============
    @api.model
    def get_employee_list(self):
        """Return list of active employees (id, name) for the picker."""
        try:
            employees = self.env['hr.employee'].sudo().search_read(
                domain=[('active', '=', True)],
                fields=['id', 'name', 'job_title', 'department_id'],
                order='name asc',
                limit=500,
            )
            for e in employees:
                e['department'] = e['department_id'][1] if e.get('department_id') else ''
                e.pop('department_id', None)
            return employees
        except Exception as e:
            _logger.warning("hr_dashboard: employee list failed: %s", e)
            return []

    @api.model
    def get_employee_spotlight(self, employee_id, date_from=None, date_to=None):
        """Detailed profile + KPIs for a single employee."""
        if not employee_id:
            return {}

        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')

        emp = _safe(lambda: self.env['hr.employee'].sudo().browse(int(employee_id)).exists(),
                    None, 'employee_browse')
        if not emp:
            return {'error': 'Employee not found'}

        # Avatar URL (Odoo serves binary images at /web/image/<model>/<id>/<field>)
        avatar = f'/web/image/hr.employee/{emp.id}/image_512'

        # Basic profile (defensive field access)
        def _f(field, default=None):
            return getattr(emp, field, default) if hasattr(emp, field) else default

        profile = {
            'id': emp.id,
            'name': emp.name or '',
            'avatar': avatar,
            'job_title': _f('job_title') or '',
            'job_id_name': (_f('job_id') and emp.job_id.name) or '',
            'department': (_f('department_id') and emp.department_id.name) or '',
            'manager': (_f('parent_id') and emp.parent_id.name) or '',
            'work_email': _f('work_email') or '',
            'work_phone': _f('work_phone') or '',
            'mobile_phone': _f('mobile_phone') or '',
            'work_location': (_f('work_location_id') and emp.work_location_id.name) or _f('work_location') or '',
            'company': (_f('company_id') and emp.company_id.name) or '',
            'gender': _f('sex') or _f('gender') or '',
            'employee_type': _f('employee_type') or '',
        }

        # Current contract / hr.version (Odoo 19 unified contract+employee versioning)
        version_info = {}
        if 'hr.version' in self.env:
            try:
                Version = self.env['hr.version'].sudo()
                # Pick the most recent version for this employee
                v = Version.search(
                    [('employee_id', '=', emp.id)],
                    order='date_version desc' if 'date_version' in Version._fields else 'id desc',
                    limit=1,
                )
                if v:
                    version_info = {
                        'name': v.display_name or '',
                        'wage': float(getattr(v, 'wage', 0) or 0),
                        'date_start': str(getattr(v, 'contract_date_start', '') or ''),
                        'date_end': str(getattr(v, 'contract_date_end', '') or ''),
                        'date_version': str(getattr(v, 'date_version', '') or ''),
                        'contract_type': (getattr(v, 'contract_type_id', None) and v.contract_type_id.name) or '',
                        'wage_type': getattr(v, 'wage_type', '') or '',
                        'schedule_pay': getattr(v, 'schedule_pay', '') or '',
                        'resource_calendar': (getattr(v, 'resource_calendar_id', None) and v.resource_calendar_id.name) or '',
                    }
            except Exception as e:
                _logger.warning("hr_dashboard: version info failed: %s", e)

        # KPIs for this employee
        kpis = {
            'pending_leaves': self._safe_count('hr.leave', [
                ('employee_id', '=', emp.id),
                ('state', 'in', ('confirm', 'draft')),
            ]),
            'approved_leaves': self._safe_count('hr.leave', [
                ('employee_id', '=', emp.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
            ]),
            'attendances': self._safe_count('hr.attendance', [
                ('employee_id', '=', emp.id),
                ('check_in', '>=', f'{date_from} 00:00:00'),
                ('check_in', '<=', f'{date_to} 23:59:59'),
            ]),
            'pending_expenses': 0,
            'expense_total': 0.0,
            'payslip_count': 0,
            'payslip_total': 0.0,
            'appraisals_pending': 0,
            'appraisals_done': 0,
        }

        # Appraisal counts for this employee (Odoo 19 Enterprise)
        # States: '1_new' (Draft), '2_pending' (Ongoing), '3_done' (Done)
        if 'hr.appraisal' in self.env:
            kpis['appraisals_pending'] = self._safe_count('hr.appraisal', [
                ('employee_id', '=', emp.id),
                ('state', 'not in', ('3_done', 'done', 'cancel')),
            ])
            kpis['appraisals_done'] = self._safe_count('hr.appraisal', [
                ('employee_id', '=', emp.id),
                ('state', 'in', ('3_done', 'done')),
            ])

        # Expenses for this employee
        if 'hr.expense' in self.env:
            for state_val in ('reported', 'submitted', 'draft'):
                c = self._safe_count('hr.expense', [
                    ('employee_id', '=', emp.id), ('state', '=', state_val),
                ])
                if c:
                    kpis['pending_expenses'] = c
                    break
            amount_field = None
            for cand in ('total_amount', 'total_amount_currency', 'untaxed_amount', 'price_total'):
                if self._has_field('hr.expense', cand):
                    amount_field = cand
                    break
            if amount_field:
                kpis['expense_total'] = round(_safe(lambda: sum(
                    self.env['hr.expense'].sudo().search([
                        ('employee_id', '=', emp.id),
                        ('date', '>=', date_from),
                        ('date', '<=', date_to),
                    ]).mapped(amount_field)
                ), 0.0), 2)

        # Payslips (Enterprise: hr_payroll provides hr.payslip)
        last_payslip = {}
        if 'hr.payslip' in self.env:
            try:
                Payslip = self.env['hr.payslip'].sudo()
                slips = Payslip.search([('employee_id', '=', emp.id)], order='date_to desc')
                kpis['payslip_count'] = len(slips)
                # Compute total of net (or basic) for the date range
                net_field = None
                for cand in ('net_wage', 'amount_net', 'gross_wage', 'basic_wage'):
                    if self._has_field('hr.payslip', cand):
                        net_field = cand
                        break
                if net_field:
                    range_slips = slips.filtered(
                        lambda s: s.date_to and date_from <= str(s.date_to) <= date_to
                    ) if 'date_to' in Payslip._fields else slips
                    kpis['payslip_total'] = round(sum(range_slips.mapped(net_field) or [0.0]), 2)
                if slips:
                    s = slips[0]
                    last_payslip = {
                        'id': s.id,
                        'number': getattr(s, 'number', '') or s.display_name or '',
                        'date_from': str(getattr(s, 'date_from', '') or ''),
                        'date_to': str(getattr(s, 'date_to', '') or ''),
                        'state': getattr(s, 'state', '') or '',
                        'net_wage': float(getattr(s, net_field, 0) or 0) if net_field else 0.0,
                    }
            except Exception as e:
                _logger.warning("hr_dashboard: payslip info failed: %s", e)

        return {
            'profile': profile,
            'version': version_info,
            'kpis': kpis,
            'last_payslip': last_payslip,
            'payroll_installed': 'hr.payslip' in self.env,
            'date_from': date_from,
            'date_to': date_to,
        }

    @api.model
    def print_employee_payslip(self, payslip_id):
        """Return a report action to print a payslip — fall back to opening the form."""
        if not payslip_id or 'hr.payslip' not in self.env:
            return {}
        slip = self.env['hr.payslip'].sudo().browse(int(payslip_id)).exists()
        if not slip:
            return {}
        # Standard Odoo payslip report
        report_xmlid = 'hr_payroll.action_report_payslip'
        try:
            report = self.env.ref(report_xmlid, raise_if_not_found=False)
            if report:
                action = report.report_action(slip)
                # Make sure the client receives JSON-serializable data
                if isinstance(action, dict):
                    action['context'] = action.get('context') or {}
                    return action
        except Exception as e:
            _logger.warning("hr_dashboard: payslip print failed: %s", e)
        # Fallback — open the payslip form so the user can use the Action menu
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'res_id': slip.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ============ Approvals Center ============
    @api.model
    def get_pending_approvals(self, limit=10):
        """Fetch pending leave and expense requests."""
        result = {
            'leaves': [],
            'expense_sheets': [],
            'appraisals': [],
            'has_expense_module': 'hr.expense' in self.env,
            'has_leave_module': 'hr.leave' in self.env,
            'has_appraisal_module': 'hr.appraisal' in self.env,
        }

        # Pending leaves
        if 'hr.leave' in self.env:
            try:
                Leave = self.env['hr.leave']
                leaves = Leave.search(
                    [('state', 'in', ('confirm', 'validate1'))],
                    order='create_date desc', limit=limit,
                )
                for lv in leaves:
                    result['leaves'].append({
                        'id': lv.id,
                        'employee_name': lv.employee_id.name if lv.employee_id else '',
                        'employee_id': lv.employee_id.id if lv.employee_id else False,
                        'avatar': f'/web/image/hr.employee/{lv.employee_id.id}/avatar_128' if lv.employee_id else False,
                        'leave_type': lv.holiday_status_id.name if lv.holiday_status_id else '',
                        'date_from': str(lv.date_from or '')[:10],
                        'date_to': str(lv.date_to or '')[:10],
                        'number_of_days': float(getattr(lv, 'number_of_days', 0) or 0),
                        'name': lv.name or '',
                        'state': lv.state,
                        'department': lv.department_id.name if getattr(lv, 'department_id', False) else '',
                    })
            except Exception as e:
                _logger.warning("hr_dashboard: pending leaves fetch failed: %s", e)

        # Pending expenses — show drafts + submitted (matches the dashboard KPI definition).
        # In Odoo 19, the 'submitted' state is often skipped entirely in auto-approve workflows,
        # so a manager's "expenses to review" really means everything in draft or submitted.
        result['has_expense_module'] = 'hr.expense' in self.env

        if 'hr.expense' in self.env:
            try:
                Expense = self.env['hr.expense']
                expenses = Expense.search(
                    [('state', 'in', ('draft', 'submitted'))],
                    order='create_date desc', limit=limit,
                )

                amount_field = None
                for cand in ('total_amount', 'total_amount_currency', 'untaxed_amount', 'price_total'):
                    if cand in Expense._fields:
                        amount_field = cand
                        break

                for exp in expenses:
                    emp = exp.employee_id if getattr(exp, 'employee_id', False) else None
                    result['expense_sheets'].append({
                        'id': exp.id,
                        'name': exp.name or '',
                        'employee_name': emp.name if emp else '',
                        'employee_id': emp.id if emp else False,
                        'avatar': f'/web/image/hr.employee/{emp.id}/avatar_128' if emp else False,
                        'total_amount': float(getattr(exp, amount_field, 0) or 0) if amount_field else 0.0,
                        'currency': exp.currency_id.symbol if getattr(exp, 'currency_id', False) else '',
                        'expense_count': 1,
                        'state': exp.state,
                        'department': exp.department_id.name if getattr(exp, 'department_id', False) else '',
                        'create_date': str(exp.create_date)[:10] if exp.create_date else '',
                    })
            except Exception as e:
                _logger.warning("hr_dashboard: pending expenses fetch failed: %s", e)

        # Pending appraisals (Odoo 19 Enterprise)
        if 'hr.appraisal' in self.env:
            try:
                appraisal_data = self._get_appraisal_data(limit=limit)
                result['appraisals'] = appraisal_data.get('pending_list', [])
            except Exception as e:
                _logger.warning("hr_dashboard: pending appraisals fetch failed: %s", e)

        return result

    @api.model
    def approve_leave(self, leave_id):
        try:
            leave = self.env['hr.leave'].browse(int(leave_id)).exists()
            if not leave:
                return {'ok': False, 'error': 'Leave not found'}
            if leave.state == 'confirm':
                leave.action_approve()
            else:
                leave.action_validate()
            return {'ok': True, 'message': f'Leave for {leave.employee_id.name} approved'}
        except Exception as e:
            _logger.warning("hr_dashboard: approve_leave failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @api.model
    def refuse_leave(self, leave_id):
        try:
            leave = self.env['hr.leave'].browse(int(leave_id)).exists()
            if not leave:
                return {'ok': False, 'error': 'Leave not found'}
            leave.action_refuse()
            return {'ok': True, 'message': f'Leave for {leave.employee_id.name} refused'}
        except Exception as e:
            _logger.warning("hr_dashboard: refuse_leave failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @api.model
    def approve_expense_sheet(self, sheet_id):
        """Approve an expense (Odoo 19: hr.expense).

        Odoo 19 flow: draft → submitted → approved → posted → in_payment → paid

        Smart handling based on current state:
        - 'draft':    Submit first (action_submit_expenses), then approve
        - 'submitted': Approve directly (action_approve)
        - 'approved': Already approved; no-op success
        """
        if 'hr.expense' not in self.env:
            return {'ok': False, 'error': 'Expenses module not installed'}
        try:
            exp = self.env['hr.expense'].browse(int(sheet_id)).exists()
            if not exp:
                return {'ok': False, 'error': 'Expense not found'}

            current = exp.state
            name = exp.name or 'Expense'

            if current in ('approved', 'posted', 'in_payment', 'paid'):
                return {'ok': True, 'message': f'{name} already approved'}

            # If in draft, submit first
            if current == 'draft':
                # Try common Odoo 19 submit methods
                submitted = False
                for method_name in ('action_submit_expenses', 'action_submit'):
                    if hasattr(exp, method_name):
                        try:
                            getattr(exp, method_name)()
                            submitted = True
                            break
                        except Exception as e:
                            _logger.info("hr_dashboard: %s failed: %s", method_name, e)
                            continue
                if not submitted:
                    # Fallback: direct write
                    exp.sudo().write({'state': 'submitted'})
                # Refresh to read new state
                exp.invalidate_recordset(['state'])

            # Now approve
            approved = False
            for method_name in ('action_approve', 'approve_expense'):
                if hasattr(exp, method_name):
                    try:
                        getattr(exp, method_name)()
                        approved = True
                        break
                    except Exception as e:
                        _logger.info("hr_dashboard: %s failed: %s", method_name, e)
                        continue
            if not approved:
                exp.sudo().write({'state': 'approved'})

            exp.invalidate_recordset(['state'])
            return {'ok': True, 'message': f'{name} approved'}
        except Exception as e:
            _logger.warning("hr_dashboard: approve expense failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @api.model
    def refuse_expense_sheet(self, sheet_id, reason='Refused from dashboard'):
        """Refuse an expense (Odoo 19: hr.expense)."""
        if 'hr.expense' not in self.env:
            return {'ok': False, 'error': 'Expenses module not installed'}
        try:
            exp = self.env['hr.expense'].browse(int(sheet_id)).exists()
            if not exp:
                return {'ok': False, 'error': 'Expense not found'}
            name = exp.name or 'Expense'

            refused = False
            for method_name in ('action_refuse', 'refuse_expense'):
                if hasattr(exp, method_name):
                    try:
                        try:
                            getattr(exp, method_name)(reason)
                        except TypeError:
                            getattr(exp, method_name)()
                        refused = True
                        break
                    except Exception as e:
                        _logger.info("hr_dashboard: %s failed: %s", method_name, e)
                        continue
            if not refused:
                exp.sudo().write({'state': 'refused'})

            return {'ok': True, 'message': f'{name} refused'}
        except Exception as e:
            _logger.warning("hr_dashboard: refuse expense failed: %s", e)
            return {'ok': False, 'error': str(e)}

    # ============ Appraisals (Odoo 19 Enterprise) ============
    def _get_appraisal_data(self, date_from=None, date_to=None, limit=10):
        """Fetch appraisal KPIs + pending appraisals + chart data."""
        if 'hr.appraisal' not in self.env:
            return {}
        try:
            Appraisal = self.env['hr.appraisal']
            today = fields.Date.today()

            # Detect state values available in this Odoo version
            state_sel = {}
            try:
                state_sel = dict(Appraisal._fields['state']._description_selection(self.env))
            except Exception:
                pass

            # Odoo 19 hr.appraisal states: '1_new' (Draft), '2_pending' (Ongoing), '3_done' (Done)
            # (no cancel state in Odoo 19). Older Odoo used: 'new', 'pending', 'done', 'cancel'.
            # Robust strategy: anything NOT a "done" state is pending.
            done_states = [s for s in ('3_done', 'done') if s in state_sel] or ['3_done', 'done']
            terminal_states = list(done_states) + [s for s in ('cancel', 'cancelled', 'canceled') if s in state_sel]

            # KPIs — use NOT-IN for pending so we don't have to guess names
            pending_count = self._safe_count(
                'hr.appraisal', [('state', 'not in', terminal_states)], 'appraisal_pending'
            )
            done_count = 0
            if date_from and date_to:
                date_field = 'date_close' if 'date_close' in Appraisal._fields else 'write_date'
                done_count = self._safe_count('hr.appraisal', [
                    ('state', 'in', done_states),
                    (date_field, '>=', date_from),
                    (date_field, '<=', date_to + ' 23:59:59'),
                ], 'appraisal_done')
            else:
                done_count = self._safe_count('hr.appraisal', [('state', 'in', done_states)], 'appraisal_done')

            # Upcoming (next 30 days)
            upcoming = 0
            date_field = None
            for cand in ('date_close', 'date_final_interview'):
                if cand in Appraisal._fields:
                    date_field = cand
                    break
            if date_field:
                in_30 = (today + timedelta(days=30)).strftime('%Y-%m-%d')
                upcoming = self._safe_count('hr.appraisal', [
                    ('state', 'not in', terminal_states),
                    (date_field, '>=', str(today)),
                    (date_field, '<=', in_30),
                ], 'appraisal_upcoming')

            # Pending list (for approvals center) — also NOT-IN
            pending_list = []
            try:
                appraisals = Appraisal.search([('state', 'not in', terminal_states)],
                                              order='create_date desc', limit=limit)
                for a in appraisals:
                    emp = a.employee_id if getattr(a, 'employee_id', False) else None
                    pending_list.append({
                        'id': a.id,
                        'employee_name': emp.name if emp else '',
                        'employee_id': emp.id if emp else False,
                        'avatar': f'/web/image/hr.employee/{emp.id}/avatar_128' if emp else False,
                        'state': a.state,
                        'state_label': state_sel.get(a.state, a.state),
                        'date_close': str(getattr(a, 'date_close', '') or '')[:10],
                        'manager': (getattr(a, 'manager_ids', False) and ', '.join(a.manager_ids.mapped('name'))) or '',
                        'department': (getattr(a, 'department_id', False) and a.department_id.name) or '',
                    })
            except Exception as e:
                _logger.warning("hr_dashboard: appraisal pending list failed: %s", e)

            # Chart: appraisals by state
            by_state = []
            for code, label in state_sel.items():
                cnt = self._safe_count('hr.appraisal', [('state', '=', code)])
                if cnt:
                    by_state.append({'name': label, 'count': cnt})

            return {
                'pending_count': pending_count,
                'done_count': done_count,
                'upcoming_count': upcoming,
                'pending_list': pending_list,
                'by_state': by_state,
            }
        except Exception as e:
            _logger.warning("hr_dashboard: appraisal section failed: %s", e)
            return {}

    @api.model
    def approve_appraisal(self, appraisal_id):
        """Advance an appraisal through the Odoo 19 workflow.

        Based on the actual hr.appraisal source code in Odoo 19:
            '1_new' (Draft) → '2_pending' (Ongoing): action_confirm() just does self.state = '2_pending'
            '2_pending' (Ongoing) → '3_done' (Done): action_done() REQUIRES assessment_note (Final Rating)

        action_done() filters out appraisals without assessment_note and returns a
        notification — it does NOT raise. So a silent "no-op" is the symptom of a
        missing Final Rating.

        Strategy:
        - From 1_new: call action_confirm() (works without prerequisites)
        - From 2_pending: ensure assessment_note exists (auto-pick a default if missing),
          then call action_done(). This bypasses the silent failure.
        """
        if 'hr.appraisal' not in self.env:
            return {'ok': False, 'error': 'Appraisals module not installed'}
        try:
            a = self.env['hr.appraisal'].browse(int(appraisal_id)).exists()
            if not a:
                return {'ok': False, 'error': 'Appraisal not found'}

            current = a.state
            emp_name = a.employee_id.name if a.employee_id else 'employee'

            # Already done
            if current == '3_done':
                return {'ok': True, 'message': f'Appraisal for {emp_name} already done'}

            # Draft → Ongoing
            if current == '1_new':
                if hasattr(a, 'action_confirm'):
                    a.action_confirm()
                else:
                    a.write({'state': '2_pending'})
                return {'ok': True, 'message': f'Appraisal for {emp_name} confirmed (now Ongoing)'}

            # Ongoing → Done — requires assessment_note (Final Rating)
            if current == '2_pending':
                if not a.assessment_note and 'hr.appraisal.note' in self.env:
                    # Auto-pick a default rating so action_done() doesn't silently fail.
                    # Prefer the company's default if set; otherwise grab any active note.
                    default_note = False
                    try:
                        if a.company_id and getattr(a.company_id, 'appraisal_assessment_note_ids', False):
                            default_note = a.company_id.appraisal_assessment_note_ids[:1]
                    except Exception:
                        pass
                    if not default_note:
                        default_note = self.env['hr.appraisal.note'].sudo().search(
                            [('company_id', 'in', (a.company_id.id, False))], limit=1
                        )
                    if default_note:
                        a.sudo().write({'assessment_note': default_note.id})

                # Now try action_done — it should work since assessment_note is set
                if hasattr(a, 'action_done'):
                    try:
                        result = a.action_done()
                    except Exception as e:
                        _logger.warning("hr_dashboard: action_done failed: %s; falling back to direct write", e)
                        a.sudo().write({'state': '3_done'})

                # Verify state actually changed (action_done can silently filter)
                a.invalidate_recordset(['state'])
                if a.state != '3_done':
                    # Last resort: direct write
                    a.sudo().write({'state': '3_done'})

                return {'ok': True, 'message': f'Appraisal for {emp_name} marked as done'}

            return {'ok': False, 'error': f'Unexpected state: {current}'}
        except Exception as e:
            _logger.warning("hr_dashboard: approve_appraisal failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @api.model
    def cancel_appraisal(self, appraisal_id):
        """Reset an appraisal back to Draft (Odoo 19 has no cancel state).

        Odoo 19 hr.appraisal source provides action_back() which sets state back to '1_new'
        and clears the assessment_note. That's the closest thing to "cancel" in Odoo 19 —
        and for our dashboard purposes (manager wants to take the appraisal out of the
        pending queue without marking it done), this is the right action.
        """
        if 'hr.appraisal' not in self.env:
            return {'ok': False, 'error': 'Appraisals module not installed'}
        try:
            a = self.env['hr.appraisal'].browse(int(appraisal_id)).exists()
            if not a:
                return {'ok': False, 'error': 'Appraisal not found'}
            emp_name = a.employee_id.name if a.employee_id else 'employee'

            if a.state == '1_new':
                return {'ok': True, 'message': f'Appraisal for {emp_name} already in Draft'}

            if hasattr(a, 'action_back'):
                a.action_back()
            else:
                a.sudo().write({'state': '1_new', 'assessment_note': False})
            return {'ok': True, 'message': f'Appraisal for {emp_name} reset to Draft'}
        except Exception as e:
            _logger.warning("hr_dashboard: cancel_appraisal failed: %s", e)
            return {'ok': False, 'error': str(e)}
