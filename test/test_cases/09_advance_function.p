//&S-
//&T-
//&D-

advFunc;

earlyReturn( value: integer ): integer
begin
    return value;
    value := value + 1;
    return value + 1;
    return 0;
end
end

recursive( index: integer ): integer
begin
    if ( index = 1 ) then  
    begin
        return 1;
    end
    else
    begin
        return recursive( index-1 )+index;
    end
    end if
end 
end

begin

var a : integer;
a := earlyReturn(10);
print a;
print recursive(a);

end
end