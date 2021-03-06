#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
## This file is part of Tango Control System:  http://www.tango-controls.org/
##
## $Author: Sergi Rubio Manrique, srubio@cells.es
## copyleft :    ALBA Synchrotron Controls Section, www.cells.es
##
## Tango Control System is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as published
## by the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## Tango Control System is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
#############################################################################

"""
PyTangoArchiving.schemas: This module provides the Schemas object; 
a singleton to detect and manage multiple archiving schemas.
"""

import traceback,time,re
import fandango
import fandango.functional as fun
from fandango import clmatch

import sys
EXPERT_MODE = any(a in str(sys.argv) for a in 
        ('ArchivingBrowser.py','ctarchiving','taurustrend',
         'taurusfinder','ctsearch','ipython', 'test',
         'archiving2csv','archiving2plot','matlab'))

class Schemas(object):
    """ Schemas kept in a singleton object """
    
    SCHEMAS = fandango.SortedDict()
    MODULES = {'fandango':fun,'fun':fun} #Limited access to fandango library
    LOCALS = fandango.functional.__dict__.copy()
    
    @classmethod
    def keys(k):
        return k.SCHEMAS.keys()
    
    @classmethod
    def load(k,tango='',prop=''):
        tangodb = fandango.tango.get_database(tango)
        schemas = prop or tangodb.get_property('PyTangoArchiving','Schemas')['Schemas']
        if not schemas:
          schemas = ['tdb','hdb']
          tangodb.put_property('PyTangoArchiving',{'Schemas':schemas})
        [k.getSchema(schema,tango) for schema in schemas]
        return k.SCHEMAS
    
    @classmethod
    def getSchema(k,schema,tango='',prop='',logger=None):
        
        if schema.startswith('#') and EXPERT_MODE:
            schema = schema.strip('#')
            print('%s available only in EXPERT_MODE'%schema)

        if schema in k.SCHEMAS:
          # Failed schemas should be also returned (to avoid unneeded retries)
          return k.SCHEMAS[schema]
        
        dct = {'schema':schema,'dbname':schema,
               'match':clmatch,'clmatch':clmatch} 

        try:
          tango = fandango.tango.get_database(tango)
          props = prop or tango.get_property('PyTangoArchiving',schema)[schema]
          if fandango.isSequence(props):
            props = [map(str.strip,t.split('=',1)) for t in props]
          dct.update(props)
          
          rd = dct.get('reader')
          if rd:
            m = rd.split('(')[0].rsplit('.',1)[0]
            c = rd[len(m)+1:]
            if m not in k.MODULES:
              fandango.evalX('import %s'%m,modules=k.MODULES)
            #print('getSchema(%s): load %s reader'%(schema,dct.get('reader')))
            dct['logger'] = logger 
            dct['reader'] = rd = fandango.evalX(
                        dct.get('reader'),
                        modules=k.MODULES,
                        _locals=dct)
            
            if not hasattr(rd,'is_attribute_archived'):
              rd.is_attribute_archived = lambda *a,**k:True
            if not hasattr(rd,'get_attributes'):
              rd.get_attributes = lambda *a,**k:[]
            if not hasattr(rd,'get_attribute_values'):
              if dct['method']:
                rd.get_attribute_values = getattr(rd,dct['method'])

            if not hasattr(rd,'schema'): rd.schema = dct['schema']

        except Exception,e:
            print('Reader.getSchema(%s): failed!'%schema)
            if logger: 
                try: logger.debug(traceback.format_exc())
                except: pass
            dct = None
          
        k.SCHEMAS[schema] = dct
        return dct
    
    @classmethod
    def checkSchema(k,schema,attribute='',start=None,end=None):
      #print('In reader.Schemas.checkSchema(%s,%s,%s,%s)'%(schema,attribute,start,end))
      schema = k.getSchema(schema)
      if not schema: return False
      f = schema.get('check')
      if not f: 
        v = True
      else:
        try:
          now = time.time()
          start = fun.notNone(start,now-1)
          end = fun.notNone(end,now)
          k.LOCALS.update({'attribute':attribute,
                'match':clmatch,'clmatch':clmatch,
                'start':start,'end':end,'now':now,
                'reader':schema.get('reader'),
                'schema':schema.get('schema'),
                'dbname':schema.get('dbname',schema.get('schema','')),
                })
          #print('(%s)%%(%s)'%(f,[t for t in k.LOCALS.items() if t[0] in f]))
          v =fun.evalX(f,k.LOCALS,k.MODULES)
        except:
          traceback.print_exc()
          v =False
      #print('checkSchema(%s): %s'%(schema,v))
      return v


