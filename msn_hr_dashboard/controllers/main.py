# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _empty_payload():
    """Fallback payload so the UI can render even if the server hit a problem."""
    return {
        'kpis': {
            'total_employees': 0, 'new_hires': 0, 'present_today': 0,
            'pending_leaves': 0, 'approved_leaves': 0, 'pending_expenses': 0,
            'expense_total': 0.0, 'active_contracts': 0,
        },
        'charts': {
            'departments': [], 'leaves': [], 'attendance_trend': [],
            'growth': [], 'gender': {'male': 0, 'female': 0, 'other': 0},
            'expenses_by_category': [],
        },
        'sparklines': {'employees': [0], 'attendance': [0]},
        'date_from': '', 'date_to': '',
    }


class HRDashboardController(http.Controller):

    @http.route('/msn_hr_dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, date_from=None, date_to=None):
        try:
            config = request.env['hr.dashboard.config'].sudo().get_active_config()
        except Exception as e:
            _logger.exception("msn_hr_dashboard: could not load config: %s", e)
            config = None

        try:
            data = request.env['hr.dashboard.config'].sudo().get_dashboard_data(date_from, date_to)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: data aggregation failed: %s", e)
            data = _empty_payload()
            data['error'] = str(e)

        if config:
            data['config'] = {
                'logo': bool(config.logo) and f'/web/image/hr.dashboard.config/{config.id}/logo' or False,
                'show_logo': config.show_logo,
                'dashboard_title': config.dashboard_title or 'HR Analytics',
                'dashboard_subtitle': config.dashboard_subtitle or 'Human Resources Overview',
                'primary_color': config.primary_color or '#6366F1',
                'secondary_color': config.secondary_color or '#8B5CF6',
                'accent_color': config.accent_color or '#EC4899',
                'bg_gradient_start': config.bg_gradient_start or '#0F172A',
                'bg_gradient_mid': config.bg_gradient_mid or '#1E1B4B',
                'bg_gradient_end': config.bg_gradient_end or '#312E81',
                'card_colors': [
                    config.card_color_1 or '#6366F1',
                    config.card_color_2 or '#10B981',
                    config.card_color_3 or '#F59E0B',
                    config.card_color_4 or '#EC4899',
                    config.card_color_5 or '#EF4444',
                    config.card_color_6 or '#06B6D4',
                ],
                'text_color': config.text_color or '#F1F5F9',
                'text_muted_color': config.text_muted_color or '#94A3B8',
                'glass_opacity': config.glass_opacity if config.glass_opacity is not False else 0.1,
                'blur_intensity': config.blur_intensity or 20,
                'border_radius': config.border_radius or 20,
                'enable_animations': bool(config.enable_animations),
            }
        else:
            data['config'] = {
                'logo': False, 'show_logo': True,
                'dashboard_title': 'HR Analytics',
                'dashboard_subtitle': 'Human Resources Overview',
                'primary_color': '#6366F1', 'secondary_color': '#8B5CF6', 'accent_color': '#EC4899',
                'bg_gradient_start': '#0F172A', 'bg_gradient_mid': '#1E1B4B', 'bg_gradient_end': '#312E81',
                'card_colors': ['#6366F1', '#10B981', '#F59E0B', '#EC4899', '#EF4444', '#06B6D4'],
                'text_color': '#F1F5F9', 'text_muted_color': '#94A3B8',
                'glass_opacity': 0.1, 'blur_intensity': 20, 'border_radius': 20,
                'enable_animations': True,
            }
        return data

    # ============ Employee Spotlight endpoints ============
    @http.route('/msn_hr_dashboard/employees', type='json', auth='user')
    def get_employee_list(self):
        try:
            return request.env['hr.dashboard.config'].sudo().get_employee_list()
        except Exception as e:
            _logger.exception("msn_hr_dashboard: employee_list endpoint failed: %s", e)
            return []

    @http.route('/msn_hr_dashboard/employee_spotlight', type='json', auth='user')
    def get_employee_spotlight(self, employee_id, date_from=None, date_to=None):
        try:
            return request.env['hr.dashboard.config'].sudo().get_employee_spotlight(
                employee_id, date_from, date_to
            )
        except Exception as e:
            _logger.exception("msn_hr_dashboard: spotlight endpoint failed: %s", e)
            return {'error': str(e)}

    @http.route('/msn_hr_dashboard/print_payslip', type='json', auth='user')
    def print_payslip(self, payslip_id):
        try:
            return request.env['hr.dashboard.config'].sudo().print_employee_payslip(payslip_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: print_payslip failed: %s", e)
            return {}

    # ============ Approvals Center endpoints ============
    @http.route('/msn_hr_dashboard/pending_approvals', type='json', auth='user')
    def pending_approvals(self, limit=10):
        try:
            return request.env['hr.dashboard.config'].sudo().get_pending_approvals(limit)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: pending_approvals failed: %s", e)
            return {'leaves': [], 'expense_sheets': [], 'has_expense_module': False, 'has_leave_module': False}

    @http.route('/msn_hr_dashboard/approve_leave', type='json', auth='user')
    def approve_leave(self, leave_id):
        try:
            # Approval methods need real user context (not sudo) for proper validation
            return request.env['hr.dashboard.config'].approve_leave(leave_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: approve_leave failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @http.route('/msn_hr_dashboard/refuse_leave', type='json', auth='user')
    def refuse_leave(self, leave_id):
        try:
            return request.env['hr.dashboard.config'].refuse_leave(leave_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: refuse_leave failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @http.route('/msn_hr_dashboard/approve_expense_sheet', type='json', auth='user')
    def approve_expense_sheet(self, sheet_id):
        try:
            return request.env['hr.dashboard.config'].approve_expense_sheet(sheet_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: approve_expense_sheet failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @http.route('/msn_hr_dashboard/refuse_expense_sheet', type='json', auth='user')
    def refuse_expense_sheet(self, sheet_id, reason='Refused from dashboard'):
        try:
            return request.env['hr.dashboard.config'].refuse_expense_sheet(sheet_id, reason)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: refuse_expense_sheet failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @http.route('/msn_hr_dashboard/approve_appraisal', type='json', auth='user')
    def approve_appraisal(self, appraisal_id):
        try:
            return request.env['hr.dashboard.config'].approve_appraisal(appraisal_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: approve_appraisal failed: %s", e)
            return {'ok': False, 'error': str(e)}

    @http.route('/msn_hr_dashboard/cancel_appraisal', type='json', auth='user')
    def cancel_appraisal(self, appraisal_id):
        try:
            return request.env['hr.dashboard.config'].cancel_appraisal(appraisal_id)
        except Exception as e:
            _logger.exception("msn_hr_dashboard: cancel_appraisal failed: %s", e)
            return {'ok': False, 'error': str(e)}
