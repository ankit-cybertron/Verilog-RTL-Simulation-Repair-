// hard/broken.v
// Task: Traffic light FSM controller
//
// States: RED(00) -> GREEN(01) -> YELLOW(10) -> RED(00) -> ...
// Each state holds for N clock cycles (configured via parameter)
// Outputs: red, green, yellow — exactly one HIGH at a time
//
// BUGS INJECTED (3 FSM bugs):
//   1. YELLOW state next-state transition goes to GREEN instead of RED  (line 44)
//   2. In GREEN state, the 'green' output is not asserted (missing assign) (line 55)
//   3. Counter reset missing in RED state transition — counter never resets (line 36)
//
// The module compiles. Simulation output will be wrong.

module traffic_light (
    input  wire clk,
    input  wire rst,
    output reg  red,
    output reg  green,
    output reg  yellow
);

    parameter HOLD_CYCLES = 3;

    // State encoding
    localparam RED_S    = 2'b00;
    localparam GREEN_S  = 2'b01;
    localparam YELLOW_S = 2'b10;

    reg [1:0] state, next_state;
    reg [2:0] counter;   // counts cycles in current state

    // State register
    always @(posedge clk) begin
        if (rst) begin
            state   <= RED_S;
            counter <= 3'd0;
        end else begin
            if (counter == HOLD_CYCLES - 1) begin
                state   <= next_state;
                // BUG 3: counter <= 3'd0 is missing here
            end else begin
                counter <= counter + 3'd1;
            end
        end
    end

    // Next state logic
    always @(*) begin
        case (state)
            RED_S:    next_state = GREEN_S;
            GREEN_S:  next_state = YELLOW_S;
            YELLOW_S: next_state = GREEN_S;  // BUG 1: should be RED_S
            default:  next_state = RED_S;
        endcase
    end

    // Output logic
    always @(*) begin
        red    = 1'b0;
        green  = 1'b0;
        yellow = 1'b0;
        case (state)
            RED_S:    red    = 1'b1;
            GREEN_S:  green  = 1'b0;  // BUG 2: should be green = 1'b1
            YELLOW_S: yellow = 1'b1;
            default:  red    = 1'b1;
        endcase
    end

endmodule