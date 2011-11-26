#include <Python.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

static PyObject *CStuffError;

#define RAISE(value) PyErr_SetString(CStuffError, value);
#define fmod(a,b) (a<0?((a%b)+b)%b:a%b)

typedef struct {
	int rows;
	int cols;
	double *values;
} doublemap;

typedef struct {
	int rows;
	int cols;
	int *values;
} intmap;

static doublemap* create_doublemap(int rows, int cols) {
	doublemap* map;

	map = (doublemap*)malloc(sizeof(doublemap));
	if (!map) {
		return NULL;
	}
	map->rows = rows;
	map->cols = cols;
	map->values = (double*)malloc(sizeof(double) * rows * cols);
	if (!map->values) {
		free(map);
		return NULL;
	}
	return map;
}

static void free_doublemap(doublemap *map) {
	free(map->values);
	free(map);
}

static void set_doublemap(doublemap* map, double value) {
	int row, col, stride;
	for (row = 0; row<map->rows; row++) {
		stride = map->cols*row;
		for (col = 0; col<map->cols; col++) {
			map->values[stride+col] = value;
		}
	}
}

static doublemap* create_radial_map(int radius2, double multiplier, double(*func)(int)) {
	doublemap* map;

	double mxf;
	double value;
	int mx;
	int side;
	int row, col;
	int d;
	int stride;

	mxf = sqrt(radius2);
	mx = (int)mxf;
	side = mx*2+1;

	map = create_doublemap(side, side);
	if (!map) {
		return NULL;
	}

	for (row=0; row<side; row++) {
		stride = side*row;
		for (col=0; col<side; col++) {
			d = (row-mx)*(row-mx) + (col-mx)*(col-mx);
			if (d > radius2) {
				map->values[stride+col] = 0.0;
			} else if (d == 0) {
				map->values[stride+col] = multiplier;
			} else {
				value = (1.0 - (sqrt(d) / mxf));
				if (func) value = func(value);
				map->values[stride+col] = multiplier * value;
			}
		}
	}
	return map;
}

static int paint_radials_around_ants(doublemap* map, doublemap* radial, PyObject* ants) {
	PyObject *iterator, *item;
	int row, col, row2, col2;
	int stride, stride2;
	int rows2, cols2;

	rows2 = radial->rows/2;
	cols2 = radial->cols/2;

	iterator = PyObject_GetIter(ants);
	if (iterator == NULL) {
		return -1;
	}

	while ((item = PyIter_Next(iterator))) {
		if (!PyArg_ParseTuple(item, "ii", &row, &col)) {
			Py_DECREF(item);
			Py_DECREF(iterator);
			return -1;
		}
		Py_DECREF(item);
		for (row2=0; row2<radial->rows; row2++) {
			stride = fmod((row2 + row - rows2), map->rows) * map->cols;
			stride2 = row2 * radial->cols;
			for (col2=0; col2<radial->cols; col2++) {
				map->values[stride+fmod((col2 + col - cols2), map->cols)] += radial->values[stride2+col2];
			}
		}
	}

	Py_DECREF(iterator);

	if (PyErr_Occurred()) {
		return -1;
	}
	return 0;
}

static int fade_maps(doublemap* map1, doublemap* map2, double amount) {
	int row, col, stride, pos;
	double amount2;
	if ((map1->rows != map2->rows) || (map1->cols != map2->cols) || (amount < 0.0) || (amount > 1.0)) {
		return -1;
	}
	amount2 = 1.0 - amount;
	for (row=0; row<map1->rows; row++) {
		stride = row * map1->cols;
		for (col=0; col<map1->cols; col++) {
			pos = stride+col;
			map1->values[pos] = amount*map1->values[pos] + amount2*map2->values[pos];
		}
	}
	return 0;
}

/*
 * Screw it, we have only one game a proces, so we do shit globally
 */

static int g_rows = 0;
static int g_cols = 0;
static int g_densityradius2 = 0;
static int g_nearradius2 = 0;
static double g_nearpower = 1.0;
static doublemap *g_dmap_density = NULL;
static doublemap *g_dmap_near = NULL;
static doublemap *g_avg_density_map = NULL;
static double g_avg_density_min = -1;
static double g_avg_density_avg = -1;

static PyObject* cstuff_find_low_density_blobs(PyObject *self, PyObject *args) {
	PyObject *obj, *list1, *list2;
	int row, col;
	int stride;
	double vmax, vmin, vtmp, vavg;
	double vcount;

	doublemap *density_map;

	if (!PyArg_ParseTuple(args, "OO", &obj, &list1)) {
		return NULL;
	}

	if (!(density_map = create_doublemap(g_rows, g_cols))) {
		RAISE("Can't malloc for density map!");
		return NULL;
	}
	set_doublemap(density_map, 0.0);
	if (paint_radials_around_ants(density_map, g_dmap_density, obj)) {
		RAISE("'Painting' density failed!");
		free_doublemap(density_map);
		return NULL;
	}

	if (g_avg_density_map == NULL) {
		g_avg_density_map = density_map;
	} else {
		fade_maps(g_avg_density_map, density_map, 0.6);
		free_doublemap(density_map);
	}

	vmin = vmax = g_avg_density_map->values[0];
	for (row=0; row<g_rows; row++) {
		stride = row * g_cols;
		for (col=0; col<g_cols; col++) {
			vtmp = g_avg_density_map->values[stride+col];
			if (vtmp > vmax) vmax = vtmp;
		}
	}

	for (row=0; row<g_rows; row++) {
		list2 = PyList_GetItem(list1, row);
		stride = row * g_cols;
		for (col=0; col<g_cols; col++) {
			if (PyLong_AsLong(PyList_GetItem(list2, col)) == -2) {
				g_avg_density_map->values[stride+col] = vmax;
			} else {
				vavg += g_avg_density_map->values[stride+col];
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

	for (row=0; row<g_rows; row++) {
		stride = row * g_cols;
		for (col=0; col<g_cols; col++) {
			vtmp = g_avg_density_map->values[stride+col];
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
	for (row=0; row<g_rows; row++) {
		stride = row * g_cols;
		list2 = PyList_New(g_cols);
		for (col=0; col<g_cols; col++) {
			PyList_SetItem(list2, col, PyLong_FromLong((g_avg_density_map->values[stride+col] <= vtmp)?-1:-2));
		}
		PyList_SetItem(list1, row, list2);
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
	int rows, cols, densityradius2, nearradius2;
	double nearpower;

	if (!PyArg_ParseTuple(args, "iiiid", &rows, &cols, &densityradius2, &nearradius2, &nearpower)) {
		return NULL;
	}

	g_rows = rows;
	g_cols = cols;
	g_densityradius2 = densityradius2;
	g_nearradius2 = nearradius2;
	g_nearpower = nearpower;

	if (!(g_dmap_density = create_radial_map(g_densityradius2, 1, NULL))) {
		RAISE("Creation of radial map for density failed");
		return NULL;
	}
	if (!(g_dmap_near = create_radial_map(g_nearradius2, 1, NULL))) {
		RAISE("Creation of radial map for 'near' failed");
		return NULL;
	}

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
