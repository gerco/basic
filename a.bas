PRINT "Start of program"

IF 1=1 THEN 
    PRINT  "  " & 1+2+3
    PRINT  "  " & 3+4+5 
    
    IF 1 = 1 THEN 
        PRINT "    One equals One"
    END
    
ELSE 

    PRINT "Whu?" 

END

x = 0
FOR i=1 TO 10
    x = x + i
    print "  The total is " & x
END

y=0
loop2:
    y=y+1
    print "    The value of y is " & y
    if y < 10 then 
        goto loop2 
    end

PRINT "End of program"
