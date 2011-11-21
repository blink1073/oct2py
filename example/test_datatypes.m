
function test = test_datatypes()
% Test of returning a structure with multiple
% nesting and multiple return types

%%%%%%%%%%%%%%%
% numeric types
% integers
test.num.int.int8 = int8(-2^7);
test.num.int.int16 = int16(-2^15);
test.num.int.int32 = int32(-2^31);
test.num.int.int64 = int64(-2^63);
test.num.int.uint8 = uint8(2^8-1);
test.num.int.uint16 = uint16(2^16-1);
test.num.int.uint32 = uint32(2^32-1);
test.num.int.uint64 = uint64(2^64-1);

%floats
test.num.float32 = single(pi);
test.num.float64 = double(pi);
test.num.complex = 3 + 1j;
test.num.complex_matrix = (1 + 1j) * rand([2 2])

% misc
test.num.inf = inf
test.num.NaN = NaN
test.num.matrix = [1 2; 3 4]
test.num.vector = [1 2 3 4]
test.num.column_vector = [1;2;3;4]
test.num.matrix3d = rand([2 3 4])
test.num.matrix5d = rand(1,2,3,4,5)


%%%%%%%%%%%%%%%
% logical type
test.logical = [10 20 30 40 50] > 30

%%%%%%%%%%%%%%%
% string types
test.string.basic = 'spam'
test.string.char_array = {'spam', 'eggs'; 'foo ', 'bar '}
test.string.cell_array = {'spam', 'eggs'}

%%%%%%%%%%%%%%%
% struct types
test.struct.array(1).name = 'Sharon'
test.struct.array(1).age = 31
test.struct.array(2).name = 'Bill'
test.struct.array(2).age = 42

%%%%%%%%%%%%%%%
% cell array types
test.cell.vector = {'spam', 4.0, [1 2 3]}
test.cell.matrix = {'Bob', 40; 'Pam', 41}




