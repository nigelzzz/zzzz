//&S-
//&T-
//&D-

condition;

var gv: integer;
var gc: 2;

sum(a,b: integer): integer
begin
	var c: integer;
	c := a + b;
	return c;
end
end

begin

var lv: integer;

gv := 1;
lv := 3;

// Should execute then statement.
if ( gv = 1 ) then
begin
    print gv;
end
end if
// Should be executed.
print lv;

// Should execute else statement.
if ( sum(gv, gc) > 4 ) then
begin
    print gv;
end
else
begin
    print lv;
end
end if

end
end
