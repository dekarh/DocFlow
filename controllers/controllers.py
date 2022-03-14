# -*- coding: utf-8 -*-
from flectra import http

class FlectraFirstModule(http.Controller):
    @http.route('/flectra_first_module/flectra_first_module/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/flectra_first_module/flectra_first_module/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('flectra_first_module.listing', {
            'root': '/flectra_first_module/flectra_first_module',
            'objects': http.request.env['flectra_first_module.flectra_first_module'].search([]),
        })

    @http.route('/flectra_first_module/flectra_first_module/objects/<model("flectra_first_module.flectra_first_module"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('flectra_first_module.object', {
            'object': obj
        })