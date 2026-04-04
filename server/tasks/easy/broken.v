// easy/broken.v
// Task: 4-bit synchronous counter with synchronous reset
// BUGS INJECTED (3 total):
//   1. Line 10: output port declared as 'input' instead of 'output'
//   2. Line 18: undeclared wire 'carry' used but never declared
//   3. Line 20: sensitivity list uses 'negedge' instead of 'posedge'
//
// The agent must fix all 3 bugs so the module compiles and simulates correctly.

module counter_4bit (
    input  wire        clk,
    input  wire        rst,      // synchronous reset, active high
    input  wire [3:0]  count     // BUG 1: should be 'output reg [3:0] count'
);

    always @(negedge clk) begin  // BUG 3: should be 'posedge clk'
        if (rst) begin
            count <= 4'b0000;
        end else begin
            count <= count + carry; // BUG 2: 'carry' is undeclared, should be 4'b0001
        end
    end

endmodule