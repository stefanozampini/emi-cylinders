Point(1) = {0, 0, 0, 0.2};
Point(2) = {3, 0, 0, 0.2};
Point(3) = {3, 3, 0, 0.2};
Point(4) = {0, 3, 0, 0.2};

Point(5) = {1, 1, 0, 0.2};
Point(6) = {2, 1, 0, 0.2};
Point(7) = {2, 2, 0, 0.2};
Point(8) = {1, 2, 0, 0.2};
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};
Line(5) = {5, 6};
Line(6) = {6, 7};
Line(7) = {7, 8};
Line(8) = {8, 5};
Line Loop(9) = {7, 8, 5, 6};
Plane Surface(10) = {9};
Line Loop(11) = {3, 4, 1, 2};
Plane Surface(12) = {9, 11};
Physical Surface(13) = {10};
Physical Surface(14) = {12};
Physical Line(15) = {7, 6, 5, 8};