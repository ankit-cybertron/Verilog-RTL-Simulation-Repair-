// medium/testbench.v
// Testbench for alu_4bit — 10 test vectors

`timescale 1ns/1ps

module tb_alu_4bit;
    reg  [3:0] a, b;
    reg  [1:0] op;
    wire [3:0] result;
    wire       zero;
    integer    failed = 0;

    alu_4bit dut (.a(a), .b(b), .op(op), .result(result), .zero(zero));

    task check;
        input [3:0] exp_result;
        input       exp_zero;
        input [7:0] vid;
        begin
            if (result === exp_result && zero === exp_zero)
                $display("VECTOR %0d: PASS expected_result=%0d expected_zero=%0d actual_result=%0d actual_zero=%0d", vid, exp_result, exp_zero, result, zero);
            else begin
                $display("VECTOR %0d: FAIL expected_result=%0d expected_zero=%0d actual_result=%0d actual_zero=%0d", vid, exp_result, exp_zero, result, zero);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        // ADD operations (op=00)
        a=4'd3;  b=4'd5;  op=2'b00; #10; check(4'd8,  1'b0, 0); // 3+5=8
        a=4'd0;  b=4'd0;  op=2'b00; #10; check(4'd0,  1'b1, 1); // 0+0=0, zero=1
        a=4'd15; b=4'd1;  op=2'b00; #10; check(4'd0,  1'b1, 2); // overflow: 15+1=16→0

        // SUB operations (op=01)
        a=4'd7;  b=4'd3;  op=2'b01; #10; check(4'd4,  1'b0, 3); // 7-3=4
        a=4'd5;  b=4'd5;  op=2'b01; #10; check(4'd0,  1'b1, 4); // 5-5=0, zero=1
        a=4'd2;  b=4'd9;  op=2'b01; #10; check(4'd9,  1'b0, 5); // 4-bit: 2-9=9 (underflow)

        // AND operations (op=10)
        a=4'b1100; b=4'b1010; op=2'b10; #10; check(4'b1000, 1'b0, 6); // 1100 & 1010 = 1000
        a=4'b0000; b=4'b1111; op=2'b10; #10; check(4'b0000, 1'b1, 7); // 0 & F = 0, zero=1

        // OR operations (op=11)
        a=4'b1100; b=4'b0011; op=2'b11; #10; check(4'b1111, 1'b0, 8); // 1100 | 0011 = 1111
        a=4'b0000; b=4'b0000; op=2'b11; #10; check(4'b0000, 1'b1, 9); // 0 | 0 = 0, zero=1

        $display("SIMULATION_DONE failed=%0d", failed);
        $finish;
    end
endmodule