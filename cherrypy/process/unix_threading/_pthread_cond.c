#include "Python.h"
#include "pthread.h"
#include "structmember.h"


typedef struct {
  PyObject_HEAD
  int set;
  pthread_cond_t cond;
  pthread_mutex_t lock;
} ConditionObject;


static int cond_init( ConditionObject* self, PyObject* args, PyObject* kwargs );
static void cond_free( ConditionObject* self );
static PyObject* cond_acquire( ConditionObject* self );
static PyObject* cond_release( ConditionObject* self );
static PyObject* cond_wait( ConditionObject* self, PyObject* args );
static PyObject* cond_notify( ConditionObject* self );
static PyObject* cond_notifyAll( ConditionObject* self );

static PyMemberDef cond_members[] = { 
  {NULL} 
};

static PyMethodDef cond_methods[] = {
  { "acquire", (PyCFunction)cond_acquire, METH_NOARGS, "" },
  { "release", (PyCFunction)cond_release, METH_NOARGS, "" },
  { "wait", (PyCFunction)cond_wait, METH_VARARGS, "" },
  { "notify", (PyCFunction)cond_notify, METH_NOARGS, "" },
  { "notifyAll", (PyCFunction)cond_notifyAll, METH_NOARGS, "" },
  { NULL }
};

static PyTypeObject ConditionType  = {
  PyObject_HEAD_INIT(NULL)
  0,                         /*ob_size*/
  "_pthread_cond.Condition", /*tp_name*/
  sizeof(ConditionObject),   /*tp_basicsize*/
  0,                         /*tp_itemsize*/
  (destructor)cond_free,     /*tp_dealloc*/
  0,                         /*tp_print*/
  0,                         /*tp_getattr*/
  0,                         /*tp_setattr*/
  0,                         /*tp_compare*/
  0,                         /*tp_repr*/
  0,                         /*tp_as_number*/
  0,                         /*tp_as_sequence*/
  0,                         /*tp_as_mapping*/
  0,                         /*tp_hash */
  0,                         /*tp_call*/
  0,                         /*tp_str*/
  0,                         /*tp_getattro*/
  0,                         /*tp_setattro*/
  0,                         /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,        /*tp_flags*/
  "",                        /* tp_doc */
  0,		               /* tp_traverse */
  0,		               /* tp_clear */
  0,		               /* tp_richcompare */
  0,		               /* tp_weaklistoffset */
  0,		               /* tp_iter */
  0,		               /* tp_iternext */
  cond_methods,              /* tp_methods */
  cond_members,              /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)cond_init,       /* tp_init */
  0,                         /* tp_alloc */
  0,                         /* tp_new */
};

static int cond_init( ConditionObject* self, PyObject* args, PyObject* kwargs ) {
  self->set = 0;
  int err = pthread_mutex_init( &self->lock, NULL );
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return -1;
  }
  err = pthread_cond_init( &self->cond, NULL );
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return -1;
  }
  return 0;
}

static void cond_free( ConditionObject* self ) {
  pthread_mutex_destroy( &self->lock );
  pthread_cond_destroy( &self->cond );
}

static PyObject* cond_acquire( ConditionObject* self ) {
  int err = 0;
  Py_BEGIN_ALLOW_THREADS;
  err = pthread_mutex_lock( &self->lock );
  Py_END_ALLOW_THREADS;
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject* cond_release( ConditionObject* self ) {
  int err = pthread_mutex_unlock( &self->lock );
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject* cond_wait( ConditionObject* self, PyObject* args ) {
  // for now timed waits are not supported (it's ignored)
  int err = 0;
  while( !self->set && err != EINVAL ) {
    /*    struct timespec timeout = {0};
    timeout.tv_sec = time(0) + 4;

    Py_BEGIN_ALLOW_THREADS;
    err = pthread_cond_timedwait( &self->cond, &self->lock, &timeout );
    Py_END_ALLOW_THREADS;
    */
    Py_BEGIN_ALLOW_THREADS;
    err = pthread_cond_wait( &self->cond, &self->lock );
    Py_END_ALLOW_THREADS;
    if( PyErr_CheckSignals() ) {
      return NULL;
    }
  }
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject* cond_notify( ConditionObject* self ) {
  self->set = 1;
  int err = 0; 
  Py_BEGIN_ALLOW_THREADS;
  err = pthread_cond_signal( &self->cond );
  Py_END_ALLOW_THREADS;
  self->set = 0;
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyObject* cond_notifyAll( ConditionObject* self ) {
  self->set = 1;
  int err = 0; 
  Py_BEGIN_ALLOW_THREADS;
  err = pthread_cond_broadcast( &self->cond );
  Py_END_ALLOW_THREADS;
  self->set = 0;
  if( err != 0 ) {
    PyErr_SetFromErrno( PyExc_OSError );
    return NULL;
  }
  Py_RETURN_NONE;
}

static PyMethodDef module_methods[] = {
  {NULL}
};

PyMODINIT_FUNC
init_pthread_cond(void)
{
  ConditionType.tp_new = PyType_GenericNew;
  if( PyType_Ready( &ConditionType ) < 0 ) {
    return;
  }
  PyObject* mod = Py_InitModule( "_pthread_cond", module_methods );
  if( mod == NULL ) {
    return;
  }
  Py_INCREF( &ConditionType );
  PyModule_AddObject( mod, "Condition", (PyObject*)&ConditionType );
}
