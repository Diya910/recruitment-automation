#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import traceback
from typing import Dict, List, Any, Optional
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")  # Set to DEBUG for more detailed logs
logger.add("test_basic_flow.log", rotation="10 MB", level="DEBUG")

# Import the necessary modules
try:
    from domains.handler import (
        start_interview_session,
        process_response,
        export_session_data
    )
except ImportError as e:
    logger.error(f"Failed to import required modules: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

logger.info("Starting Basic Flow Test Script")

# Test responses
NORMAL_RESPONSES = [
    "I would design a microservices architecture for the e-commerce backend. The key microservices would include Product Service, Order Service, User Service, Payment Service, and Inventory Service. Each service would have its own database and communicate via REST APIs or message queues. This approach allows for better scalability, fault isolation, and independent deployment of services.",
    "For the RESTful API endpoints, I would implement the following:\n\n1. Product Management:\n- GET /products - List all products\n- GET /products/{id} - Get product details\n- POST /products - Create a new product\n- PUT /products/{id} - Update a product\n- DELETE /products/{id} - Delete a product\n\n2. User Orders:\n- GET /orders - List user orders\n- GET /orders/{id} - Get order details\n- POST /orders - Create a new order\n- PUT /orders/{id} - Update order status\n- GET /users/{id}/orders - Get orders for a specific user",
    "For the database schema, I would use a combination of relational and NoSQL databases:\n\n1. Products Table:\n- product_id (PK)\n- name\n- description\n- price\n- category_id (FK)\n- inventory_count\n- created_at\n- updated_at\n\n2. Customers Table:\n- customer_id (PK)\n- name\n- email\n- password_hash\n- address\n- phone\n- created_at\n\n3. Orders Table:\n- order_id (PK)\n- customer_id (FK)\n- status\n- total_amount\n- shipping_address\n- payment_method\n- created_at\n\n4. OrderItems Table:\n- item_id (PK)\n- order_id (FK)\n- product_id (FK)\n- quantity\n- price_at_purchase",
    "For user authentication and authorization, I would implement:\n\n1. JWT-based authentication system\n2. OAuth 2.0 for third-party authentication\n3. Role-based access control (RBAC) for authorization\n4. HTTPS for all communications\n5. Password hashing using bcrypt\n6. Rate limiting to prevent brute force attacks\n7. Regular security audits and penetration testing",
    "To integrate a payment gateway like Stripe, I would:\n\n1. Create a separate Payment Service microservice\n2. Implement Stripe's API for payment processing\n3. Use webhooks to handle asynchronous events (payment success, failure)\n4. Store payment tokens rather than actual card data\n5. Implement idempotency keys to prevent duplicate charges\n6. Add proper error handling and retry mechanisms\n7. Include comprehensive logging for audit trails",
    "To ensure the platform can scale to handle high traffic, I would implement:\n\n1. Horizontal scaling of microservices using Kubernetes\n2. Database sharding for large tables\n3. Caching layers using Redis for frequently accessed data\n4. CDN for static assets\n5. Asynchronous processing using message queues\n6. Database read replicas to distribute query load\n7. Auto-scaling based on traffic patterns\n8. Load balancing across multiple regions",
    "For inventory management and preventing overselling, I would implement:\n\n1. Real-time inventory tracking system\n2. Optimistic locking for inventory updates\n3. Temporary inventory holds during checkout process\n4. Scheduled inventory reconciliation jobs\n5. Notifications for low stock items\n6. Integration with warehouse management systems\n7. Fallback mechanisms for handling edge cases"
]

async def test_basic_flow():
    """Test the basic happy path flow of the HR automation tool."""
    logger.info("Testing basic flow")
    
    try:
        # Start an interview session
        logger.info("Starting interview session...")
        session_info = await start_interview_session()
        logger.debug(f"Session info: {json.dumps(session_info, default=str, indent=2)}")
        
        # Log scenario details
        if "scenario" in session_info:
            scenario = session_info["scenario"]
            logger.info(f"Using scenario: {scenario.get('id')} - {scenario.get('title')}")
            
            # Get the scenario details to check number of questions
            from domains.recruitment.scenario_manager import get_scenario_by_id
            full_scenario = get_scenario_by_id(scenario.get('id'))
            if full_scenario and "questions" in full_scenario:
                questions = full_scenario["questions"]
                logger.info(f"Scenario has {len(questions)} questions")
                logger.debug(f"Questions: {json.dumps([q['id'] for q in questions], indent=2)}")
                logger.info(f"We are providing {len(NORMAL_RESPONSES)} responses")
            else:
                logger.warning("Could not get full scenario details")
        
        session_id = session_info.get("session_id")
        
        if not session_id:
            logger.error("Failed to get session_id from start_interview_session")
            logger.error(f"Session info returned: {session_info}")
            return False
        
        logger.info(f"Started interview session with ID: {session_id}")
        
        # Process responses
        for i, response in enumerate(NORMAL_RESPONSES):
            logger.info(f"Processing response {i+1}/{len(NORMAL_RESPONSES)}")
            logger.debug(f"Response content: {response[:100]}...")
            
            try:
                result = await process_response(session_id, response)
                logger.debug(f"Process response result: {json.dumps(result, default=str, indent=2)}")
            except Exception as e:
                logger.error(f"Exception during process_response: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
            
            if "error" in result:
                logger.error(f"Error processing response {i+1}: {result['error']}")
                return False
            
            # Check if interview is complete
            if result.get("status") == "completed":
                logger.info("Interview completed successfully")
                
                # Export the session data
                try:
                    export_result = export_session_data(session_id)
                    logger.debug(f"Export result: {json.dumps(export_result, default=str, indent=2)}")
                    
                    if "error" in export_result:
                        logger.error(f"Error exporting session data: {export_result['error']}")
                    else:
                        logger.info(f"Exported session data to: {export_result.get('export_path')}")
                except Exception as e:
                    logger.error(f"Exception during export_session_data: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                
                return True
            
            logger.info(f"Interview not yet complete after response {i+1}")
            logger.debug(f"Current state: awaiting_clarification={result.get('awaiting_clarification', False)}")
            
            # Check if we're waiting for clarification
            if result.get("awaiting_clarification"):
                logger.info("System is awaiting clarification, providing additional response")
                clarification_response = "Let me clarify my previous answer. " + response
                logger.info("Sending clarification response")
                
                try:
                    clarification_result = await process_response(session_id, clarification_response)
                    logger.debug(f"Clarification result: {json.dumps(clarification_result, default=str, indent=2)}")
                    
                    if "error" in clarification_result:
                        logger.error(f"Error processing clarification response: {clarification_result['error']}")
                        return False
                    
                    # Check if interview is complete after clarification
                    if clarification_result.get("status") == "completed":
                        logger.info("Interview completed successfully after clarification")
                        
                        # Export the session data
                        try:
                            export_result = export_session_data(session_id)
                            logger.debug(f"Export result: {json.dumps(export_result, default=str, indent=2)}")
                            
                            if "error" in export_result:
                                logger.error(f"Error exporting session data: {export_result['error']}")
                            else:
                                logger.info(f"Exported session data to: {export_result.get('export_path')}")
                        except Exception as e:
                            logger.error(f"Exception during export_session_data: {str(e)}")
                            logger.error(f"Traceback: {traceback.format_exc()}")
                        
                        return True
                    
                    # Update result to the clarification result for the next iteration
                    result = clarification_result
                except Exception as e:
                    logger.error(f"Exception during clarification process_response: {str(e)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return False
        
        # If we get here, the interview wasn't completed with the provided responses
        logger.warning("Interview not completed with provided responses")
        logger.warning("This could be because the interview requires more responses than provided")
        return False
    
    except Exception as e:
        logger.error(f"Error in test_basic_flow: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run the basic flow test and report results."""
    logger.info("Starting HR Automation Basic Flow Test")
    
    # Run the basic flow test
    result = await test_basic_flow()
    
    # Report result
    if result:
        logger.info("Basic Flow Test: PASSED")
    else:
        logger.error("Basic Flow Test: FAILED")
    
    return result

if __name__ == "__main__":
    asyncio.run(main())