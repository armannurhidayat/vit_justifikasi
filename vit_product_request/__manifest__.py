{
    'name' : 'Product Request',
    'version' : '0.1',
    'category': 'Purchase Management',
    'images' : [],
    'depends' : ['stock',
                 'account',
                 'purchase',
                 'purchase_requisition',
                 'hr',],
    'author' : 'vitraining.com',
    'description': """
User Purchase Request
==========================================
* Allow department users to request product to be purchased 
* Allow Purchase Manager to create Call For Bid per Product requested, then RFQ, and PO
* Join many request lines into single Call for Bid
* Display total RFQ amount under Call for Bids 

    """,
    'website': 'http://www.vitraining.com',
    'data': [
        'wizard/product_request_line_wizard.xml',
        'views/menu.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/product_request.xml',
        'views/pr.xml',
        'views/po.xml',
        'views/picking.xml',
        'views/department.xml',
        #'reports/product_request.xml',
    ],
    'test': [
    ],
    'demo': [],
    'installable': True,
    'auto_install': False
}