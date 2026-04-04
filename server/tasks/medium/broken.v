// medium/broken.v
// Task: 4-bit ALU supporting ADD, SUB, AND, OR operations
//
// BUGS INJECTED (2 semantic — compiles fine, wrong simulation output):
//   1. SUB operation uses '+' instead of '-'  (line 24)
//   2. AND operation uses '|' instead of '&'  (line 27)
//
// The module compiles cleanly with iverilog.
// The agent cannot see compile errors — it must deduce bugs from
// simulation output mismatches.

module alu_4bit (
    input  wire [3:0]  a,
    input  wire [3:0]  b,
    input  wire [1:0]  op,      // 00=ADD 01=SUB 10=AND 11=OR
    output reg  [3:0]  result,
    output reg         zero     // 1 when result == 0
);

    always @(*) begin
        case (op)
            2'b00: result = a + b;           // ADD  — correct
            2'b01: result = a + b;           // SUB  — BUG 1: should be a - b
            2'b10: result = a | b;           // AND  — BUG 2: should be a & b
            2'b11: result = a | b;           // OR   — correct
            default: result = 4'b0000;
        endcase
        zero = (result == 4'b0000) ? 1'b1 : 1'b0;
    end

endmodule