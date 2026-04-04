// easy/correct.v — reference solution (NOT given to agent)
// Used to generate golden_output.txt

module counter_4bit (
    input  wire        clk,
    input  wire        rst,
    output reg  [3:0]  count
);

    always @(posedge clk) begin
        if (rst) begin
            count <= 4'b0000;
        end else begin
            count <= count + 4'b0001;
        end
    end

endmodule