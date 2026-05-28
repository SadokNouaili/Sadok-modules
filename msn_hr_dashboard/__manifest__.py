# -*- coding: utf-8 -*-
{
    'name': 'All in One HR Dashboard ',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Interactive HR dashboard with glassmorphism design, customizable colors and logo',
    'description': """
HR Dashboard
============
A modern, interactive dashboard for Odoo 19 HR modules with:

* Glassmorphism design with gradients
* KPI cards with sparklines and trend indicators
* Interactive charts (bar, line, pie, doughnut)
* Date range filters
* Drill-down to records
* Animated counters and smooth transitions
* Fully customizable colors and logo from Settings
* RTL support with Arabic translation included

Covers: Employees, Attendance, Leaves, Expenses, Departments, Versions (contracts).
    """,
    'author': 'Msn',
    'website': '',
    'license': 'OPL-1',
    'price': 120.00,
    'currency': 'USD',
    'depends': [
        'base',
        'web',
        'hr',
        'hr_attendance',
        'hr_holidays',
        'hr_expense',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/dashboard_config_data.xml',
        'views/dashboard_config_views.xml',
        'views/dashboard_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'msn_hr_dashboard/static/lib/chart.umd.min.js',
            'msn_hr_dashboard/static/src/scss/dashboard.scss',
            'msn_hr_dashboard/static/src/components/**/*.js',
            'msn_hr_dashboard/static/src/components/**/*.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
