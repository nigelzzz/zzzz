//&S-
//&T-
//&D-

realtest2;

var gv : real;
var gc : 4;

sum(a, b: real): real
begin
	var result: real;
	result := a + b;
	return result;
end
end

begin

var lv : real;
var lc : -2.2;
lv := -1.1;
print sum(lv, lc);

// NOTE: Initially, lv and lc are assigned as 1.1 and 2.2, respectively;
// however, when loaded incorrectly as integers, the binary representation of 1.1
// (00111111100011001100110011001101b) appears to still be less than that
// of 2.2 (01000000000011001100110011001101b). To address this issue, we assign
// lv as -1.1 (10111111100011001100110011001101b) and lv as -2.2
// (11000000000011001100110011001101b), ensuring that their relative order is
// inverted if not loaded correctly.
if( lv > lc ) then
begin
    print lv;
end
else
begin
    print lc;
end
end if

gv := 2.0;
print (gv / gc);

end
end
