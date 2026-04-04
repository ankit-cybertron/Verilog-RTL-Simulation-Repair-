// hard/correct.v — reference solution (NOT given to agent)

module traffic_light (
    input  wire clk,
    input  wire rst,
    output reg  red,
    output reg  green,
    output reg  yellow
);

    parameter HOLD_CYCLES = 3;

    localparam RED_S    = 2'b00;
    localparam GREEN_S  = 2'b01;
    localparam YELLOW_S = 2'b10;

    reg [1:0] state, next_state;
    reg [2:0] counter;

    always @(posedge clk) begin
        if (rst) begin
            state   <= RED_S;
            counter <= 3'd0;
        end else begin
            if (counter == HOLD_CYCLES - 1) begin
                state   <= next_state;
                counter <= 3'd0;       // fixed: counter resets on transition
            end else begin
                counter <= counter + 3'd1;
            end
        end
    end

    always @(*) begin
        case (state)
            RED_S:    next_state = GREEN_S;
            GREEN_S:  next_state = YELLOW_S;
            YELLOW_S: next_state = RED_S;   // fixed: back to RED
            default:  next_state = RED_S;
        endcase
    end

    always @(*) begin
        red    = 1'b0;
        green  = 1'b0;
        yellow = 1'b0;
        case (state)
            RED_S:    red    = 1'b1;
            GREEN_S:  green  = 1'b1;  // fixed: assert green
            YELLOW_S: yellow = 1'b1;
            default:  red    = 1'b1;
        endcase
    end

endmodule