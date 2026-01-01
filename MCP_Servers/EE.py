import random
from fastmcp import FastMCP

mcp = FastMCP("EE_MCP_Server")



@mcp.tool()
def create_customer(Price_Plan: str) -> str:
    """Create a customer with the given Price_Plan."""
    Customer_ID = random.randint(1000, 9999)
    Customer_ID = str(Customer_ID)
    return f"Customer created: Cutomer ID is {Customer_ID}, Price_Plan: {Price_Plan}"

@mcp.tool()
def add_soc(Customer_ID: str, SOC: str) -> str:
    """Add SOC to a customer."""
    return f"Done adding SOC {SOC} to Customer ID: {Customer_ID}"

if __name__ == "__main__":
    mcp.run(transport="stdio")