#include <Python.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

/*
 * Screw it, we have only one game a proces, so we do shit globally
 */

static int g_rows = 0;
static int g_cols = 0;
static int g_densityradius2 = 0;
static double *g_dmap = NULL;
static int g_dmap_center = 0;
static int g_dmap_side = 0;
static double *g_avg_density_map = NULL;
static double g_avg_density_min = -1;
static double g_avg_density_avg = -1;

static PyObject *CStuffError;

#define RAISE(value) PyErr_SetString(CStuffError, value);
#define fmod(a,b) (a < 0?((a%b)+b)%b:a%b)

static void init_densityradius(void) {
	double mxf;
	int mx;
	int side;
	int row, col;
	int d;
	int stride;

	mxf = sqrt(g_densityradius2);
	g_dmap_center = mx = (int)mxf;
	g_dmap_side = side = mx*2+1;

	if (!(g_dmap = (double*)malloc(sizeof(double) * side * side))) {
		RAISE("Can't malloc for density map!");
		return;
	}

	for (row=0; row<side; row++) {
		stride = side*row;
		for (col=0; col<side; col++) {
			d = (row-mx)*(row-mx) + (col-mx)*(col-mx);
			if (d > g_densityradius2) {
				g_dmap[stride+col] = 0.0;
			} else if (d == 0) {
				g_dmap[stride+col] = 1.0;
			} else {
				g_dmap[stride+col] = 1.0 - (sqrt(d) / mxf);
			}
		}
	}
}

static PyObject* cstuff_find_low_density_blobs(PyObject *self, PyObject *args) {
	PyObject *obj, *iterator, *item, *tmp, *list1, *list2;
	int row, col, row2, col2;
	int stride, stride2;
	double vmax, vmin, vtmp, vavg;
	double vcount;

	double *density_map;

	if (!PyArg_ParseTuple(args, "OO", &obj, &list1)) {
		return NULL;
	}

	iterator = PyObject_GetIter(obj);
	if (iterator == NULL) {
		return NULL;
	}

	if (!(density_map = (double*)malloc(sizeof(double)*g_rows*g_cols))) {
		RAISE("Can't malloc for density map!");
		return NULL;
	}
	for (row2=0; row2<g_rows; row2++) {
		stride2 = row2 * g_cols;
		for (col2=0; col2<g_cols; col2++) {
			density_map[stride2+col2] = 0.0;
		}
	}

	while ((item = PyIter_Next(iterator))) {
		/* Dunno if I can use PyArg_ParseTuple(), #python channel wasn't too helpful */
		if ((tmp = PyTuple_GetItem(item, 0)) == NULL) {
			Py_DECREF(item);
			Py_DECREF(iterator);
			return NULL;
		}
		row = PyLong_AsLong(tmp);
		if ((tmp = PyTuple_GetItem(item, 1)) == NULL) {
			Py_DECREF(item);
			Py_DECREF(iterator);
			return NULL;
		}
		col = PyLong_AsLong(tmp);
		Py_DECREF(item);
		for (row2=0; row2<g_dmap_side; row2++) {
			stride = fmod((row2 + row - g_dmap_center), g_rows) * g_cols;
			stride2 = row2 * g_dmap_side;
			fflush(stdout);
			for (col2=0; col2<g_dmap_side; col2++) {
				density_map[stride+fmod((col2 + col - g_dmap_center), g_cols)] += g_dmap[stride2+col2];
			}
		}
	}

	Py_DECREF(iterator);

	if (PyErr_Occurred()) {
		return NULL;
	}

	if (g_avg_density_map == NULL) {
		g_avg_density_map = density_map;
	} else {
		for (row2=0; row2<g_rows; row2++) {
			stride2 = row2 * g_cols;
			for (col2=0; col2<g_cols; col2++) {
				g_avg_density_map[stride2+col2] = 0.6*g_avg_density_map[stride2+col2] + 0.4*density_map[stride2+col2];
			}
		}
		free(density_map);
	}

	vmin = vmax = g_avg_density_map[0];
	for (row2=0; row2<g_rows; row2++) {
		stride2 = row2 * g_cols;
		for (col2=0; col2<g_cols; col2++) {
			vtmp = g_avg_density_map[stride2+col2];
			if (vtmp > vmax) vmax = vtmp;
		}
	}

	for (row2=0; row2<g_rows; row2++) {
		list2 = PyList_GetItem(list1, row2);
		stride2 = row2 * g_cols;
		for (col2=0; col2<g_cols; col2++) {
			if (PyLong_AsLong(PyList_GetItem(list2, col2)) == -2) {
				g_avg_density_map[stride2+col2] = vmax;
			} else {
				vavg += g_avg_density_map[stride2+col2];
				vcount += 1;
			}
		}
	}
	vavg /= vcount;
	if (g_avg_density_avg < 0) {
		g_avg_density_avg = vavg;
	} else {
		g_avg_density_avg = 0.9*g_avg_density_avg + 0.1*vavg;
	}

	for (row2=0; row2<g_rows; row2++) {
		stride2 = row2 * g_cols;
		for (col2=0; col2<g_cols; col2++) {
			vtmp = g_avg_density_map[stride2+col2];
			if (vtmp < vmin) vmin = vtmp;
		}
	}
	if (g_avg_density_min < 0) {
		g_avg_density_min = vmin;
	} else {
		g_avg_density_min = 0.9*g_avg_density_min + 0.1*vmin;
	}

	vtmp = g_avg_density_min + 0.1*(g_avg_density_avg-g_avg_density_min);

	list1 = PyList_New(g_rows);
	for (row2=0; row2<g_rows; row2++) {
		stride2 = row2 * g_cols;
		list2 = PyList_New(g_cols);
		for (col2=0; col2<g_cols; col2++) {
			PyList_SetItem(list2, col2, PyLong_FromLong((g_avg_density_map[stride2+col2] <= vtmp)?-1:-2));
		}
		PyList_SetItem(list1, row2, list2);
	}


	return list1;
}

static PyObject* cstuff_vector_ants_speedup(PyObject *self, PyObject *args) {
	int ra, ca, ir, ic;
	if (!PyArg_ParseTuple(args, "ii(ii)", &ra, &ca, &ir, &ic)) {
		return NULL;
	}

	ir -= ra;
	if (abs(ir) > g_rows/2) {
		if (ir > 0) {
			ir -= g_rows;
		} else {
			ir += g_rows;
		}
	}

	ic -= ca;
	if (abs(ic) > g_cols/2) {
		if (ic > 0) {
			ic -= g_cols;
		} else {
			ic += g_cols;
		}
	}

	return Py_BuildValue("iii", ((ir*ir)+(ic*ic)), ir, ic);
}

static PyObject* cstuff_init(PyObject *self, PyObject *args) {
	int rows, cols, densityradius2;

	if (!PyArg_ParseTuple(args, "iii", &rows, &cols, &densityradius2)) {
		return NULL;
	}

	g_rows = rows;
	g_cols = cols;
	g_densityradius2 = densityradius2;

	init_densityradius();

	Py_RETURN_NONE;
}

static PyMethodDef cstuff_methods[] = {
	{"init",  cstuff_init, METH_VARARGS, ""},
	{"find_low_density_blobs", cstuff_find_low_density_blobs, METH_VARARGS, ""},
	{"vector_ants_speedup", cstuff_vector_ants_speedup, METH_VARARGS, ""},
	{NULL, NULL, 0, NULL}
};

static struct PyModuleDef cstuff_module = {
	PyModuleDef_HEAD_INIT,
	"cstuff",
	"C stuff for flantob ant bot",
	-1,
	cstuff_methods
};

PyMODINIT_FUNC PyInit_cstuff(void) {
	PyObject *module;
	module = PyModule_Create(&cstuff_module);
	if (module == NULL) return NULL;

	CStuffError = PyErr_NewException("spam.CStuffError", NULL, NULL);
	Py_INCREF(CStuffError);
	PyModule_AddObject(module, "CStuffError", CStuffError);

	return module;
}
