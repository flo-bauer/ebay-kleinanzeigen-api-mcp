"""Tool implementations for Kleinanzeigen MCP Server."""
import logging
from typing import Optional, List, Union
from mcp.server.fastmcp import FastMCP

from ..client import KleinanzeigenClient

logger = logging.getLogger(__name__)


def register_listing_tools(mcp: FastMCP):
    """Register all listing-related MCP tools (FastMCP mode)."""
    
    @mcp.tool()
    async def search_listings(
        query: Optional[str] = None,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        page_count: int = 1
    ) -> str:
        """
        Search eBay Kleinanzeigen (kleinanzeigen.de) for items with filters.
        
        IMPORTANT: This is your ONLY access to eBay Kleinanzeigen / kleinanzeigen.de!
        Use this tool for ALL search queries for local offers, used items,
        or classified ads in Germany.
        
        Args:
            query: Search terms for the item (e.g., "stereo speakers", "home theater", "bicycle", "laptop")
            location: Postal code or city (e.g., "78464", "Constance", "79206", "Berlin")
            radius: Search radius in kilometers around location (e.g., 5, 10, 20, 50)
            min_price: Minimum price in EUR (e.g., 50)
            max_price: Maximum price in EUR (e.g., 500)
            page_count: Number of result pages to fetch (1-20, default: 1)
        
        Returns:
            Formatted list of search results including titles, prices, and URLs.
            Each listing contains: ID, title, price, short description, and direct link.
        
        Examples:
            - Stereo speakers in Constance: query="stereo speakers", location="78464", radius=20
            - Cheap laptops: query="laptop", max_price=300
            - Multiple pages: query="gaming pc", page_count=3
            - Alternative search: query="home theater speakers", location="79206"
        """
        return await _search_listings_impl(query, location, radius, min_price, max_price, page_count)
    
    @mcp.tool()
    async def get_listing_details(listing_id: str) -> str:
        """
        Get complete details for an eBay Kleinanzeigen listing.
        
        Use this tool after search_listings to get all information for a
        specific item: complete description, all images,
        seller info and technical details.
        
        Args:
            listing_id: The unique listing ID from search results (e.g., "2937345678")
        
        Returns:
            Formatted string with complete listing information:
            - Full title and description
            - Current status (active, sold, reserved)
            - Price and shipping options
            - Location details
            - Number of views
            - All image URLs
            - Technical details and features
            - Seller information
        
        Examples:
            - Get details: listing_id="2937345678"
            - After search: Use the "adid" from search_listings results
        """
        return await _get_listing_details_impl(listing_id)
    
    logger.info("Registered listing tools: search_listings, get_listing_details")


def register_listing_tools_manual(server):
    """Register all listing-related MCP tools (manual mode for SSE)."""
    from mcp.types import Tool
    from mcp import types
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_listings",
                description="""Search eBay Kleinanzeigen (kleinanzeigen.de) for items with filters.
        
IMPORTANT: This is your ONLY access to eBay Kleinanzeigen / kleinanzeigen.de!
Use this tool for ALL search queries for local offers, used items,
or classified ads in Germany.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search terms for the item (e.g., 'stereo speakers', 'home theater', 'bicycle', 'laptop')"
                        },
                        "location": {
                            "type": "string",
                            "description": "Postal code or city (e.g., '78464', 'Constance', '79206', 'Berlin')"
                        },
                        "radius": {
                            "type": "integer",
                            "description": "Search radius in kilometers around location (e.g., 5, 10, 20, 50)"
                        },
                        "min_price": {
                            "type": "integer",
                            "description": "Minimum price in EUR (e.g., 50)"
                        },
                        "max_price": {
                            "type": "integer",
                            "description": "Maximum price in EUR (e.g., 500)"
                        },
                        "page_count": {
                            "type": "integer",
                            "description": "Number of result pages to fetch (1-20, default: 1)",
                            "default": 1
                        }
                    }
                }
            ),
            Tool(
                name="get_listing_details",
                description="""Get complete details for an eBay Kleinanzeigen listing.
        
Use this tool after search_listings to get all information for a
specific item: complete description, all images,
seller info and technical details.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "listing_id": {
                            "type": "string",
                            "description": "The unique listing ID from search results (e.g., '2937345678')"
                        }
                    },
                    "required": ["listing_id"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "search_listings":
            result = await _search_listings_impl(
                query=arguments.get("query"),
                location=arguments.get("location"),
                radius=arguments.get("radius"),
                min_price=arguments.get("min_price"),
                max_price=arguments.get("max_price"),
                page_count=arguments.get("page_count", 1)
            )
        elif name == "get_listing_details":
            result = await _get_listing_details_impl(
                listing_id=arguments["listing_id"]
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return [types.TextContent(type="text", text=result)]
    
    logger.info("Registered listing tools (manual): search_listings, get_listing_details")


# Shared implementation functions
async def _search_listings_impl(
    query: Optional[str] = None,
    location: Optional[str] = None,
    radius: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    page_count: int = 1
) -> str:
    """Shared implementation for search_listings."""
    async with KleinanzeigenClient() as client:
        try:
            results = await client.search_listings(
                query=query,
                location=location,
                radius=radius,
                min_price=min_price,
                max_price=max_price,
                page_count=page_count
            )
            
            if not results:
                # Build context for "no results" message
                filters = []
                if query:
                    filters.append(f"query: {query}")
                if location:
                    filters.append(f"location: {location}")
                if min_price or max_price:
                    price_range = f"{min_price or 0}€ - {max_price or '∞'}€"
                    filters.append(f"price: {price_range}")
                
                filter_text = ", ".join(filters) if filters else "no filters"
                return f"No listings found for search ({filter_text}). Try broader criteria."
            
            # Format results for Claude
            output_lines = [
                f"Found {len(results)} listings:",
                ""
            ]
            
            for idx, listing in enumerate(results, 1):
                price_display = f"{listing.price}€" if listing.price else "Preis auf Anfrage"
                output_lines.append(f"{idx}. [{listing.title}]")
                output_lines.append(f"   ID: {listing.adid}")
                output_lines.append(f"   Price: {price_display}")
                if listing.description:
                    # Truncate long descriptions
                    desc = listing.description[:100] + "..." if len(listing.description) > 100 else listing.description
                    output_lines.append(f"   Description: {desc}")
                output_lines.append(f"   URL: {listing.url}")
                # Include images if available
                if listing.images:
                    output_lines.append(f"   Images ({len(listing.images)}):")
                    for img_idx, img_url in enumerate(listing.images[:3], 1):
                        output_lines.append(f"     {img_idx}. {img_url}")
                    if len(listing.images) > 3:
                        output_lines.append(f"     ... and {len(listing.images) - 3} more")
                output_lines.append("")
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return f"Search error: {str(e)}. Please check your parameters and try again."


async def _get_listing_details_impl(listing_id: str) -> str:
    """Shared implementation for get_listing_details."""
    async with KleinanzeigenClient() as client:
        try:
            details = await client.get_listing_details(listing_id)
            
            # Format comprehensive output for Claude
            output_lines = [
                f"=== LISTING DETAILS ===",
                "",
                f"Title: {details.title}",
                f"ID: {details.id}",
                f"Status: {details.status}",
                f"Price: {details.price}€" if details.price else "Price: On request",
                f"Views: {details.views}",
                ""
            ]
            
            # Categories
            if details.categories:
                output_lines.append(f"Categories: {' > '.join(details.categories)}")
                output_lines.append("")
            
            # Description
            if details.description:
                output_lines.append("Description:")
                output_lines.append(details.description)
                output_lines.append("")
            
            # Location and delivery
            if details.location:
                output_lines.append(f"Location: {details.location.get('raw', 'Not specified')}")
            if details.delivery:
                delivery_text = "Pickup only" if details.delivery == "pickup" else "Shipping available"
                output_lines.append(f"Delivery: {delivery_text}")
            if details.location or details.delivery:
                output_lines.append("")
            
            # Images
            if details.images:
                output_lines.append(f"Images ({len(details.images)}):")
                for idx, img_url in enumerate(details.images[:5], 1):  # Limit to first 5
                    output_lines.append(f"  {idx}. {img_url}")
                if len(details.images) > 5:
                    output_lines.append(f"  ... and {len(details.images) - 5} more")
                output_lines.append("")
            
            # Details section
            if details.details:
                output_lines.append("Details:")
                for key, value in details.details.items():
                    output_lines.append(f"  {key}: {value}")
                output_lines.append("")
            
            # Features
            if details.features:
                output_lines.append("Features:")
                for key, value in details.features.items():
                    output_lines.append(f"  {key}: {value}")
                output_lines.append("")
            
            # Seller information
            if details.seller:
                output_lines.append("Seller:")
                for key, value in details.seller.items():
                    output_lines.append(f"  {key}: {value}")
                output_lines.append("")
            
            output_lines.append(f"View online: https://www.kleinanzeigen.de/s-anzeige/{details.id}")
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"Failed to fetch listing details: {e}", exc_info=True)
            return f"Error fetching listing {listing_id}: {str(e)}. Please verify the ID is correct."