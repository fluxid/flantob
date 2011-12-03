#include <Python.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

static PyObject *CStuffError;

#define RAISE(value) PyErr_SetString(CStuffError, value);
#define FMOD(a,b) (a<0?((a%b)+b)%b:a%b)

typedef struct {
	int rows;
	int cols;
	int *values;
} intmap;

typedef struct {
	int rows;
	int cols;
	double *values;
} doublemap;

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
	int pos;
	for (pos = 0; pos < (map->rows*map->cols); pos++) {
		map->values[pos] = value;
	}
}

static intmap* create_intmap(int rows, int cols) {
	intmap* map;

	map = (intmap*)malloc(sizeof(intmap));
	if (!map) {
		return NULL;
	}
	map->rows = rows;
	map->cols = cols;
	map->values = (int*)malloc(sizeof(int) * rows * cols);
	if (!map->values) {
		free(map);
		return NULL;
	}
	return map;
}

static void free_intmap(intmap *map) {
	free(map->values);
	free(map);
}

static void set_intmap(intmap* map, int value) {
	int pos;
	for (pos = 0; pos < (map->rows*map->cols); pos++) {
		map->values[pos] = value;
	}
}

static void zero_intmap(intmap* map) {
	memset(map->values, 0, map->rows*map->cols*sizeof(int));
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
static doublemap *g_near_map = NULL;
static double g_avg_density_min = -1;
static double g_avg_density_avg = -1;

static doublemap* create_radial_map(int radius2, double multiplier, double(*func)(double)) {
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
		if (row >= g_rows || col >= g_cols || row < 0 || col < 0) {
			RAISE("Invalid input data - one of the ants is out od map bounds");
			Py_DECREF(iterator);
			return -1;
		}
		for (row2=0; row2<radial->rows; row2++) {
			stride = FMOD((row2 + row - rows2), map->rows) * map->cols;
			stride2 = row2 * radial->cols;
			for (col2=0; col2<radial->cols; col2++) {
				map->values[stride+FMOD((col2 + col - cols2), map->cols)] += radial->values[stride2+col2];
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

typedef struct _stack_element {
	int row;
	int col;
	struct _stack_element* prev;
	struct _stack_element* next;
	double value;
} stack_element;

typedef struct {
	PyObject_HEAD
	doublemap* map;
	intmap* walls;
	stack_element* free_elements;
} cstuff_DirectionMap;

static stack_element* get_stack_element(cstuff_DirectionMap* obj) {
	int i;
	stack_element *element;
	if (obj->free_elements == NULL) {
		for (i = 0; i<20; i++) {
			element = (stack_element*)malloc(sizeof(stack_element));
			if (!element) {
				return NULL;
			}
			element->next = obj->free_elements;
			obj->free_elements = element;
		}
	}
	element = obj->free_elements;
	obj->free_elements = element->next;
	return element;
}

static void cstuff_DirectionMap_dealloc(cstuff_DirectionMap* self) {
	stack_element* next;
	free_doublemap(self->map);
	free_intmap(self->walls);
	next = self->free_elements;
	while (next) {
		next = next->next;
		free(next);
	}
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* cstuff_DirectionMap_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	cstuff_DirectionMap *self;
	self = (cstuff_DirectionMap*)type->tp_alloc(type, 0);
	self->map = create_doublemap(g_rows, g_cols);
	self->walls = create_intmap(g_rows, g_cols);
	self->free_elements = NULL;
	return (PyObject*)self;
}

static PyObject* cstuff_DirectionMap_clear(cstuff_DirectionMap* self) {
	set_doublemap(self->map, -1.0);
	zero_intmap(self->walls);
	Py_RETURN_NONE;
}

static PyObject* cstuff_DirectionMap_set_walls(cstuff_DirectionMap* self, PyObject *args) {
	PyObject *list1, *list2, *iterator1, *iterator2, *value;
	int whichwall;
	int row, col, stride;

	if (!PyArg_ParseTuple(args, "Oi", &list1, &whichwall)) {
		return NULL;
	}

	row = 0;
	if (!(iterator1 = PyObject_GetIter(list1))) {
		return NULL;
	}
	while ((list2 = PyIter_Next(iterator1)) && row < g_rows) {
		stride = row * g_cols;
		if (!(iterator2 = PyObject_GetIter(list2))) {
			Py_DECREF(list2);
			break;
		}
		col = 0;
		while ((value = PyIter_Next(iterator2)) && col < g_cols) {
			if (PyLong_CheckExact(value) && PyLong_AsLong(value) == whichwall) {
				self->walls->values[stride+col] = 1;
			}
			Py_DECREF(value);
			col += 1;
		}
		Py_DECREF(iterator2);
		Py_DECREF(list2);
		row += 1;
	}

	Py_DECREF(iterator1);

	if (PyErr_Occurred()) {
		return NULL;
	}

	Py_RETURN_NONE;
}

#define SETUP_ELEM(row_, col_, value_, pos_) \
	element->row = row_; \
	element->col = col_; \
	element->value = value_; \
	element->next = NULL; \
	element->prev = NULL; \
	self->map->values[pos_] = value_;

#define PUT_NEW_ELEM(row_, col_, value_, pos_) \
	element = get_stack_element(self); \
	SETUP_ELEM(row_, col_, value_, pos_) \
	if (stack) { \
		element->prev = stack_bottom; \
		stack_bottom->next = element; \
		stack_bottom = element; \
	} else { \
		stack_bottom = stack = element; \
	}

#define PUT_NEW_ELEM_WAITING(row_, col_, value_, pos_) \
	PUT_NEW_ELEM(row_, col_, value_, pos_) \
	waiting[pos_] = element;

#define PUT_NEW_ELEM_SORTED(row_, col_, value_, pos_) \
	element = waiting[pos_]; \
	if (element) { \
		if (element->next) { \
			element->next->prev = element->prev; \
		} else { \
			stack_bottom = element->prev; \
		} \
		if (element->prev) { \
			element->prev->next = element->next; \
		} else { \
			stack = element; \
		} \
	} else { \
		element = get_stack_element(self); \
		waiting[pos_] = element; \
	} \
	SETUP_ELEM(row_, col_, value_, pos_) \
	if (!stack) { \
		stack_bottom = stack = element; \
	} else if (value_ > stack_bottom->value) { \
		stack_bottom->next = element; \
		element->prev = stack_bottom; \
		stack_bottom = element; \
	} else { \
		element2 = stack_bottom; \
		while (element2->prev && element2->prev->value > value_) element2=element2->prev; \
		if (element2->prev) { \
			element2->prev->next = element; \
		} else { \
			stack = element; \
		} \
		element->prev = element2->prev; \
		element2->prev = element; \
		element->next = element2; \
	}

#define DO_STUFF(row_, col_) \
	if (!self->walls->values[pos] && self->map->values[pos] < 0) { \
		PUT_NEW_ELEM(row_, col_, value, pos); \
	}

#define DO_STUFF_NEAR(row_, col_) \
	if (!self->walls->values[pos]) { \
		value3 = value + g_near_map->values[pos]; \
		value2 = self->map->values[pos]; \
		if (value2 < 0 || value2 > value3) { \
			PUT_NEW_ELEM_SORTED(row_, col_, value3, pos); \
		} \
	}

#define RESET_STACK \
	if (stack) { \
		stack_bottom->next = self->free_elements; \
		self->free_elements = stack; \
	}

static PyObject* cstuff_DirectionMap_fill(cstuff_DirectionMap* self, PyObject *args) {
	PyObject *iterator, *item, *obj;
	int row, col, row2, col2, stride, pos;
	double value, limit;

	stack_element *element, *stack, *stack_bottom;
	stack = NULL;
	stack_bottom = NULL;

	if (!PyArg_ParseTuple(args, "Od", &obj, &limit)) {
		return NULL;
	}

	iterator = PyObject_GetIter(obj);
	if (iterator == NULL) {
		return NULL;
	}

	while ((item = PyIter_Next(iterator))) {
		if (!PyArg_ParseTuple(item, "ii", &row, &col)) {
			Py_DECREF(item);
			Py_DECREF(iterator);
			RESET_STACK;
			return NULL;
		}
		if (row >= g_rows || col >= g_cols || row < 0 || col < 0) {
			RAISE("Invalid input data - one of the targets is out od map bounds");
			Py_DECREF(iterator);
			RESET_STACK;
			return NULL;
		}
		Py_DECREF(item);
		PUT_NEW_ELEM(row, col, 0.0, row*g_cols+col);
	}
	Py_DECREF(iterator);

	if (PyErr_Occurred()) {
		RESET_STACK;
		return NULL;
	}

	while (stack) {
		element = stack;
		stack = element->next;
		row = element->row;
		col = element->col;
		value = element->value;
		stride = row*g_cols;
		value += 1.0;

		element->next = self->free_elements;
		self->free_elements = element;

		if ((limit > 0) && (value > limit)) continue;

		col2 = FMOD((col-1), g_cols);
		pos = stride+col2;
		DO_STUFF(row, col2);

		col2 = FMOD((col+1), g_cols);
		pos = stride+col2;
		DO_STUFF(row, col2);

		row2 = FMOD((row-1), g_rows);
		pos = row2*g_cols+col;
		DO_STUFF(row2, col);

		row2 = FMOD((row+1), g_rows);
		pos = row2*g_cols+col;
		DO_STUFF(row2, col);
	}

	RESET_STACK;
	Py_RETURN_NONE;
}

static PyObject* cstuff_DirectionMap_fill_near(cstuff_DirectionMap* self, PyObject *args) {
	PyObject *iterator, *item, *obj;
	int row, col, row2, col2, stride, pos;
	double value, value2, value3, limit;

	stack_element *element, *element2, *stack, *stack_bottom, **waiting;

	if (!PyArg_ParseTuple(args, "Od", &obj, &limit)) {
		return NULL;
	}

	iterator = PyObject_GetIter(obj);
	if (iterator == NULL) {
		return NULL;
	}

	if (!(waiting = (stack_element**)malloc(g_rows*g_cols*sizeof(stack_element*)))) {
		RAISE("Failed to allocate waiting nodes array");
		return NULL;
	}
	memset(waiting, 0, g_rows*g_cols*sizeof(stack_element*));

	stack = NULL;
	stack_bottom = NULL;

	while ((item = PyIter_Next(iterator))) {
		if (!PyArg_ParseTuple(item, "ii", &row, &col)) {
			Py_DECREF(item);
			Py_DECREF(iterator);
			RESET_STACK;
			free(waiting);
			return NULL;
		}
		Py_DECREF(item);
		if (row >= g_rows || col >= g_cols || row < 0 || col < 0) {
			RAISE("Invalid input data - one of the targets is out od map bounds");
			Py_DECREF(iterator);
			RESET_STACK;
			free(waiting);
			return NULL;
		}
		PUT_NEW_ELEM_WAITING(row, col, 0.0, row*g_cols+col);
	}
	Py_DECREF(iterator);

	if (PyErr_Occurred()) {
		RESET_STACK;
		free(waiting);
		return NULL;
	}
	while (stack) {
		element = stack;
		stack = element->next;
		if (stack) {
			stack->prev = NULL;
		}
		row = element->row;
		col = element->col;
		value = element->value;
		stride = row*g_cols;
		waiting[stride+col] = NULL;
		value += 1.0;

		element->next = self->free_elements;
		self->free_elements = element;

		if ((limit > 0) && (value > limit)) continue;

		col2 = FMOD((col-1), g_cols);
		pos = stride+col2;
		DO_STUFF_NEAR(row, col2)

		col2 = FMOD((col+1), g_cols);
		pos = stride+col2;
		DO_STUFF_NEAR(row, col2)

		row2 = FMOD((row-1), g_rows);
		pos = row2*g_cols+col;
		DO_STUFF_NEAR(row2, col)

		row2 = FMOD((row+1), g_rows);
		pos = row2*g_cols+col;
		DO_STUFF_NEAR(row2, col)
	}

	free(waiting);
	RESET_STACK;
	Py_RETURN_NONE;
}

#undef SETUP_ELEM
#undef PUT_NEW_ELEM
#undef PUT_NEW_ELEM_WAITING
#undef PUT_NEW_ELEM_SORTED
#undef DO_STUFF
#undef DO_STUFF_NEAR
#undef STACK

static PyObject* cstuff_DirectionMap_get_pos(cstuff_DirectionMap* self, PyObject *args) {
	int row, col;

	if (!PyArg_ParseTuple(args, "(ii)", &row, &col)) {
		return NULL;
	}
	return PyFloat_FromDouble(self->map->values[row*g_cols+col]);
}

static PyObject* cstuff_DirectionMap_get_wall(cstuff_DirectionMap* self, PyObject *args) {
	int row, col;

	if (!PyArg_ParseTuple(args, "(ii)", &row, &col)) {
		return NULL;
	}
	if (self->walls->values[row*g_cols+col]) {
		Py_RETURN_TRUE;
	} else {
		Py_RETURN_FALSE;
	}
}

static PyMethodDef cstuff_DirectionMap_methods[] = {
	{"clear", (PyCFunction)cstuff_DirectionMap_clear, METH_NOARGS, ""},
	{"set_walls", (PyCFunction)cstuff_DirectionMap_set_walls, METH_VARARGS, ""},
	{"fill", (PyCFunction)cstuff_DirectionMap_fill, METH_VARARGS, ""},
	{"fill_near", (PyCFunction)cstuff_DirectionMap_fill_near, METH_VARARGS, ""},
	{"get_pos", (PyCFunction)cstuff_DirectionMap_get_pos, METH_VARARGS, ""},
	{"get_wall", (PyCFunction)cstuff_DirectionMap_get_wall, METH_VARARGS, ""},
	{NULL}
};

static PyTypeObject cstuff_DirectionMapType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"cstuff.DirectionMap",
	sizeof(cstuff_DirectionMap),
	0,
	(destructor)cstuff_DirectionMap_dealloc,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	Py_TPFLAGS_DEFAULT,
	"",
	0,
	0,
	0,
	0,
	0,
	0,
	cstuff_DirectionMap_methods,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	0,
	cstuff_DirectionMap_new,
};

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

	vcount = 0;
	vavg = 0;
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

static double square(double x) { return x*x; }

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
	if (!(g_dmap_near = create_radial_map(g_nearradius2, g_nearpower, square))) {
		RAISE("Creation of radial map for 'near' failed");
		return NULL;
	}
	if (!(g_near_map = create_doublemap(g_rows, g_cols))) {
		RAISE("Creation of near map failed");
		return NULL;
	}

	Py_RETURN_NONE;
}

static PyObject* cstuff_do_ant_stuff(PyObject *self, PyObject *args) {
	/* Shit, making python object is hard, screw this shit then and make it objectless */
	PyObject *obj;

	if (!PyArg_ParseTuple(args, "O", &obj)) {
		return NULL;
	}

	set_doublemap(g_near_map, 0.0);
	if (paint_radials_around_ants(g_near_map, g_dmap_near, obj)) {
		RAISE("'Painting' 'near' failed!");
		return NULL;
	}

	Py_RETURN_NONE;
}

static PyObject* cstuff_get_near_value(PyObject *self, PyObject *args) {
	/* oh boy, this really sucks */
	int row, col;

	if (!PyArg_ParseTuple(args, "ii", &row, &col)) {
		return NULL;
	}

	if ((row > g_near_map->rows) || (row < 0) || (col > g_near_map->cols) || (col < 0)) {
		RAISE("Invalid values");
		return NULL;
	}

	return PyFloat_FromDouble(g_near_map->values[row*g_near_map->cols+col]);
}

static PyMethodDef cstuff_methods[] = {
	{"init",  cstuff_init, METH_VARARGS, ""},
	{"find_low_density_blobs", cstuff_find_low_density_blobs, METH_VARARGS, ""},
	{"vector_ants_speedup", cstuff_vector_ants_speedup, METH_VARARGS, ""},
	{"do_ant_stuff", cstuff_do_ant_stuff, METH_VARARGS, ""},
	{"get_near_value", cstuff_get_near_value, METH_VARARGS, ""},
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
	if (module == NULL) {
		return NULL;
	}

	if (PyType_Ready(&cstuff_DirectionMapType) < 0) {
		return NULL;
	}

	CStuffError = PyErr_NewException("cstuff.CStuffError", NULL, NULL);
	Py_INCREF(CStuffError);
	PyModule_AddObject(module, "CStuffError", CStuffError);

	Py_INCREF(&cstuff_DirectionMapType);
	PyModule_AddObject(module, "DirectionMap", (PyObject *)&cstuff_DirectionMapType);

	return module;
}
