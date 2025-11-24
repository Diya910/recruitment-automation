#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Any, Optional
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("test_hr_automation.log", rotation="10 MB", level="DEBUG")

# Import the necessary modules
try:
    from domains.handler import (
        start_interview_session,
        process_response,
        get_session_info,
        export_session_data,
        run_single_interview
    )
    from domains.recruitment.scenario_manager import get_all_scenarios, get_scenario_by_id
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

logger.info("Starting HR Automation Test Script")

# Test scenarios
NORMAL_RESPONSES = [
    "I would design a microservices architecture for the e-commerce backend. The key microservices would include Product Service, Order Service, User Service, Payment Service, and Inventory Service. Each service would have its own database and communicate via REST APIs or message queues. This approach allows for better scalability, fault isolation, and independent deployment of services.",
    "For the RESTful API endpoints, I would implement the following:\n\n1. Product Management:\n- GET /products - List all products\n- GET /products/{id} - Get product details\n- POST /products - Create a new product\n- PUT /products/{id} - Update a product\n- DELETE /products/{id} - Delete a product\n\n2. User Orders:\n- GET /orders - List user orders\n- GET /orders/{id} - Get order details\n- POST /orders - Create a new order\n- PUT /orders/{id} - Update order status\n- GET /users/{id}/orders - Get orders for a specific user",
    "For the database schema, I would use a combination of relational and NoSQL databases:\n\n1. Products Table:\n- product_id (PK)\n- name\n- description\n- price\n- category_id (FK)\n- inventory_count\n- created_at\n- updated_at\n\n2. Customers Table:\n- customer_id (PK)\n- name\n- email\n- password_hash\n- address\n- phone\n- created_at\n\n3. Orders Table:\n- order_id (PK)\n- customer_id (FK)\n- status\n- total_amount\n- shipping_address\n- payment_method\n- created_at\n\n4. OrderItems Table:\n- item_id (PK)\n- order_id (FK)\n- product_id (FK)\n- quantity\n- price_at_purchase",
    "For user authentication and authorization, I would implement:\n\n1. JWT-based authentication system\n2. OAuth 2.0 for third-party authentication\n3. Role-based access control (RBAC) for authorization\n4. HTTPS for all communications\n5. Password hashing using bcrypt\n6. Rate limiting to prevent brute force attacks\n7. Regular security audits and penetration testing",
    "To integrate a payment gateway like Stripe, I would:\n\n1. Create a separate Payment Service microservice\n2. Implement Stripe's API for payment processing\n3. Use webhooks to handle asynchronous events (payment success, failure)\n4. Store payment tokens rather than actual card data\n5. Implement idempotency keys to prevent duplicate charges\n6. Add proper error handling and retry mechanisms\n7. Include comprehensive logging for audit trails",
    "To ensure the platform can scale to handle high traffic, I would implement:\n\n1. Horizontal scaling of microservices using Kubernetes\n2. Database sharding for large tables\n3. Caching layers using Redis for frequently accessed data\n4. CDN for static assets\n5. Asynchronous processing using message queues\n6. Database read replicas to distribute query load\n7. Auto-scaling based on traffic patterns\n8. Load balancing across multiple regions",
    "For inventory management and preventing overselling, I would implement:\n\n1. Real-time inventory tracking system\n2. Optimistic locking for inventory updates\n3. Temporary inventory holds during checkout process\n4. Scheduled inventory reconciliation jobs\n5. Notifications for low stock items\n6. Integration with warehouse management systems\n7. Fallback mechanisms for handling edge cases"
]

SHORT_RESPONSES = [
    "Microservices architecture.",
    "REST APIs for products and orders.",
    "Relational DB for products, customers, orders.",
    "JWT auth and HTTPS.",
    "Stripe API integration.",
    "K8s, caching, CDN.",
    "Real-time inventory tracking."
]

LONG_RESPONSE = """
I would design a comprehensive microservices architecture for the e-commerce backend that prioritizes scalability, resilience, and maintainability. The architecture would consist of the following key microservices:

1. Product Service: Manages product catalog, categories, attributes, and search functionality.
2. Order Service: Handles order creation, processing, and management.
3. User Service: Manages user accounts, profiles, and authentication.
4. Payment Service: Integrates with payment gateways and handles payment processing.
5. Inventory Service: Tracks product inventory and prevents overselling.
6. Notification Service: Handles emails, SMS, and push notifications.
7. Analytics Service: Collects and processes business metrics and user behavior.
8. Recommendation Service: Provides personalized product recommendations.
9. Review Service: Manages product reviews and ratings.
10. Cart Service: Handles shopping cart functionality.

Each service would have its own dedicated database, chosen based on the specific requirements of that service. For instance, the Product Service might use Elasticsearch for efficient searching, while the Order Service would use a relational database for ACID compliance.

These services would communicate primarily through asynchronous messaging using a message broker like RabbitMQ or Kafka, with synchronous REST APIs used where immediate responses are required. This approach allows for better scalability, fault isolation, and independent deployment of services.

For service discovery and configuration management, I would implement a service mesh architecture using tools like Istio or Linkerd, combined with Kubernetes for container orchestration. This would provide features like load balancing, circuit breaking, and observability out of the box.

The entire system would be deployed in a cloud environment (AWS, GCP, or Azure) using infrastructure as code (Terraform or CloudFormation) and would leverage managed services where appropriate to reduce operational overhead.

For monitoring and observability, I would implement a comprehensive solution using tools like Prometheus, Grafana, and Jaeger for distributed tracing. This would allow for quick identification and resolution of issues in production.

The architecture would also include CI/CD pipelines for each service, enabling rapid and reliable deployments with automated testing at each stage.

This architecture provides a solid foundation for an e-commerce platform that can scale to handle high traffic and evolve over time as business requirements change.
"""

CODE_RESPONSE = """
For implementing the RESTful API endpoints, I would use a framework like Express.js for Node.js or Spring Boot for Java. Here's a sample implementation in Express.js:

```javascript
const express = require('express');
const router = express.Router();
const ProductController = require('../controllers/ProductController');
const OrderController = require('../controllers/OrderController');
const authMiddleware = require('../middleware/auth');

// Product endpoints
router.get('/products', ProductController.getAllProducts);
router.get('/products/:id', ProductController.getProductById);
router.post('/products', authMiddleware.isAdmin, ProductController.createProduct);
router.put('/products/:id', authMiddleware.isAdmin, ProductController.updateProduct);
router.delete('/products/:id', authMiddleware.isAdmin, ProductController.deleteProduct);

// Order endpoints
router.get('/orders', authMiddleware.isAuthenticated, OrderController.getUserOrders);
router.get('/orders/:id', authMiddleware.isAuthenticated, OrderController.getOrderById);
router.post('/orders', authMiddleware.isAuthenticated, OrderController.createOrder);
router.put('/orders/:id', authMiddleware.isAdmin, OrderController.updateOrderStatus);
router.get('/users/:id/orders', authMiddleware.isAdminOrSelf, OrderController.getUserOrders);

module.exports = router;
```

For the database schema, I would use an ORM like Sequelize or Hibernate. Here's a sample Sequelize model for the Product entity:

```javascript
const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Product = sequelize.define('Product', {
  product_id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  price: {
    type: DataTypes.DECIMAL(10, 2),
    allowNull: false
  },
  category_id: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'Categories',
      key: 'category_id'
    }
  },
  inventory_count: {
    type: DataTypes.INTEGER,
    allowNull: false,
    defaultValue: 0
  },
  created_at: {
    type: DataTypes.DATE,
    defaultValue: DataTypes.NOW
  },
  updated_at: {
    type: DataTypes.DATE,
    defaultValue: DataTypes.NOW
  }
});

module.exports = Product;
```

For handling inventory and preventing overselling, I would implement a transaction-based approach:

```javascript
async function processOrder(orderData) {
  const transaction = await sequelize.transaction();
  
  try {
    // Check inventory for all products
    for (const item of orderData.items) {
      const product = await Product.findByPk(item.product_id, { transaction });
      
      if (!product) {
        throw new Error(`Product ${item.product_id} not found`);
      }
      
      if (product.inventory_count < item.quantity) {
        throw new Error(`Insufficient inventory for product ${product.name}`);
      }
      
      // Update inventory
      await product.update({
        inventory_count: product.inventory_count - item.quantity
      }, { transaction });
    }
    
    // Create order
    const order = await Order.create({
      customer_id: orderData.customer_id,
      status: 'pending',
      total_amount: orderData.total_amount,
      shipping_address: orderData.shipping_address,
      payment_method: orderData.payment_method
    }, { transaction });
    
    // Create order items
    for (const item of orderData.items) {
      await OrderItem.create({
        order_id: order.order_id,
        product_id: item.product_id,
        quantity: item.quantity,
        price_at_purchase: item.price
      }, { transaction });
    }
    
    // Commit transaction
    await transaction.commit();
    return order;
  } catch (error) {
    // Rollback transaction on error
    await transaction.rollback();
    throw error;
  }
}
```

This implementation ensures that inventory is properly managed and prevents overselling through the use of database transactions.
"""

FOREIGN_LANGUAGE_RESPONSE = """
Pour l'architecture backend de l'e-commerce, je proposerais une architecture de microservices. Les principaux microservices seraient le Service de Produits, le Service de Commandes, le Service Utilisateur, le Service de Paiement et le Service d'Inventaire. Chaque service aurait sa propre base de données et communiquerait via des API REST ou des files d'attente de messages. Cette approche permet une meilleure évolutivité, une isolation des défaillances et un déploiement indépendant des services.

Pour les points de terminaison de l'API RESTful, j'implémentarais:
1. Gestion des produits:
   - GET /produits - Liste de tous les produits
   - GET /produits/{id} - Détails du produit
   - POST /produits - Créer un nouveau produit
   - PUT /produits/{id} - Mettre à jour un produit
   - DELETE /produits/{id} - Supprimer un produit

2. Commandes utilisateur:
   - GET /commandes - Liste des commandes
   - GET /commandes/{id} - Détails de la commande
   - POST /commandes - Créer une nouvelle commande
   - PUT /commandes/{id} - Mettre à jour l'état de la commande
   - GET /utilisateurs/{id}/commandes - Obtenir les commandes d'un utilisateur spécifique
"""

SPECIAL_CHARS_RESPONSE = """
I would design the architecture with these components:
* Product Service (manages product catalog)
* Order Service (handles orders & processing)
* User Service (manages accounts & auth)
* Payment Service (handles payments)
* Inventory Service (tracks stock)

For the database schema, I'd use:
- Products: product_id (PK), name, description, price, category_id (FK), inventory_count
- Customers: customer_id (PK), name, email, password_hash, address
- Orders: order_id (PK), customer_id (FK), status, total_amount, shipping_address
- OrderItems: item_id (PK), order_id (FK), product_id (FK), quantity, price_at_purchase

For security, I'd implement:
1️⃣ JWT authentication
2️⃣ HTTPS encryption
3️⃣ Password hashing with bcrypt
4️⃣ Rate limiting
5️⃣ Input validation & sanitization

To prevent SQL injection: Always use parameterized queries like `SELECT * FROM products WHERE id = ?` instead of string concatenation.

For XSS prevention: Escape all user input with functions like `htmlspecialchars()` in PHP or use frameworks that automatically escape output.
"""

EMPTY_RESPONSE = ""

async def test_basic_flow():
    """Test the basic happy path flow of the HR automation tool."""
    logger.info("Testing basic flow")
    
    try:
        # Start an interview session
        logger.info("Starting interview session...")
        session_info = await start_interview_session()
        logger.debug(f"Session info: {session_info}")
        session_id = session_info.get("session_id")
        
        if not session_id:
            logger.error("Failed to get session_id from start_interview_session")
            logger.error(f"Session info returned: {session_info}")
            return False
        
        logger.info(f"Started interview session with ID: {session_id}")
        
        # Process responses
        for i, response in enumerate(NORMAL_RESPONSES):
            logger.info(f"Processing response {i+1}/{len(NORMAL_RESPONSES)}")
            logger.debug(f"Response content: {response[:50]}...")
            
            result = await process_response(session_id, response)
            logger.debug(f"Process response result: {result}")
            
            if "error" in result:
                logger.error(f"Error processing response {i+1}: {result['error']}")
                return False
            
            # Check if interview is complete
            if result.get("status") == "completed":
                logger.info("Interview completed successfully")
                
                # Export the session data
                export_result = export_session_data(session_id)
                if "error" in export_result:
                    logger.error(f"Error exporting session data: {export_result['error']}")
                else:
                    logger.info(f"Exported session data to: {export_result.get('export_path')}")
                
                return True
            
            logger.info(f"Interview not yet complete after response {i+1}")
        
        # If we get here, the interview wasn't completed with the provided responses
        logger.warning("Interview not completed with provided responses")
        logger.warning("This could be because the interview requires more responses than provided")
        return False
    
    except Exception as e:
        logger.error(f"Error in test_basic_flow: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def test_edge_cases():
    """Test various edge cases."""
    logger.info("Testing edge cases")
    
    edge_cases = [
        {"name": "Short responses", "responses": SHORT_RESPONSES},
        {"name": "Long response", "responses": [LONG_RESPONSE] + NORMAL_RESPONSES[1:]},
        {"name": "Code response", "responses": [CODE_RESPONSE] + NORMAL_RESPONSES[1:]},
        {"name": "Foreign language", "responses": [FOREIGN_LANGUAGE_RESPONSE] + NORMAL_RESPONSES[1:]},
        {"name": "Special characters", "responses": [SPECIAL_CHARS_RESPONSE] + NORMAL_RESPONSES[1:]},
        {"name": "Empty response", "responses": [EMPTY_RESPONSE] + NORMAL_RESPONSES}
    ]
    
    results = {}
    
    for case in edge_cases:
        logger.info(f"Testing edge case: {case['name']}")
        
        try:
            # Start an interview session
            session_info = await start_interview_session()
            session_id = session_info.get("session_id")
            
            if not session_id:
                logger.error(f"Failed to get session_id for edge case: {case['name']}")
                results[case['name']] = False
                continue
            
            # Process responses
            for i, response in enumerate(case['responses']):
                logger.info(f"Processing response {i+1}/{len(case['responses'])}")
                result = await process_response(session_id, response)
                
                if "error" in result:
                    logger.error(f"Error processing response {i+1} for {case['name']}: {result['error']}")
                    results[case['name']] = False
                    break
                
                # Check if interview is complete
                if result.get("status") == "completed":
                    logger.info(f"Interview completed successfully for edge case: {case['name']}")
                    results[case['name']] = True
                    break
            
            # If we get here and haven't set a result, the interview wasn't completed
            if case['name'] not in results:
                logger.warning(f"Interview not completed for edge case: {case['name']}")
                results[case['name']] = False
        
        except Exception as e:
            logger.error(f"Error in edge case {case['name']}: {str(e)}")
            results[case['name']] = False
    
    logger.info(f"Edge case results: {results}")
    return results

async def test_error_handling():
    """Test error handling and recovery."""
    logger.info("Testing error handling")
    
    error_tests = [
        {"name": "Invalid session ID", "test": lambda: process_response("invalid_session_id", NORMAL_RESPONSES[0])},
        {"name": "Invalid scenario ID", "test": lambda: start_interview_session("invalid_scenario_id")},
        {"name": "Get info for non-existent session", "test": lambda: get_session_info("non_existent_session")}
    ]
    
    results = {}
    
    for test in error_tests:
        logger.info(f"Running error test: {test['name']}")
        
        try:
            result = await test["test"]()
            
            # Check if the result contains an error
            if "error" in result:
                logger.info(f"Error test {test['name']} passed: {result['error']}")
                results[test['name']] = True
            else:
                logger.warning(f"Error test {test['name']} failed: No error returned")
                results[test['name']] = False
        
        except Exception as e:
            logger.error(f"Unexpected exception in error test {test['name']}: {str(e)}")
            results[test['name']] = False
    
    logger.info(f"Error handling test results: {results}")
    return results

async def test_concurrent_interviews():
    """Test handling of concurrent interviews."""
    logger.info("Testing concurrent interviews")
    
    # Create tasks for multiple concurrent interviews
    tasks = []
    for i in range(3):  # Run 3 concurrent interviews
        logger.info(f"Setting up concurrent interview {i+1}")
        tasks.append(run_single_interview(None, NORMAL_RESPONSES))
    
    # Run interviews concurrently
    try:
        results = await asyncio.gather(*tasks)
        
        # Check results
        success_count = 0
        for i, result in enumerate(results):
            if "error" not in result:
                logger.info(f"Concurrent interview {i+1} completed successfully")
                success_count += 1
            else:
                logger.error(f"Concurrent interview {i+1} failed: {result['error']}")
        
        logger.info(f"Concurrent interviews: {success_count}/{len(tasks)} successful")
        return success_count == len(tasks)
    
    except Exception as e:
        logger.error(f"Error in concurrent interviews test: {str(e)}")
        return False

async def main():
    """Run all tests and report results."""
    logger.info("Starting HR Automation tests")
    
    # Check if scenarios are available
    scenarios = get_all_scenarios()
    if not scenarios:
        logger.error("No scenarios available. Tests cannot proceed.")
        return
    
    logger.info(f"Found {len(scenarios)} scenarios")
    
    # Run tests
    test_results = {
        "basic_flow": await test_basic_flow(),
        "edge_cases": await test_edge_cases(),
        "error_handling": await test_error_handling(),
        "concurrent_interviews": await test_concurrent_interviews()
    }
    
    # Report results
    logger.info("Test Results:")
    logger.info(f"Basic Flow: {'PASSED' if test_results['basic_flow'] else 'FAILED'}")
    
    edge_case_results = test_results['edge_cases']
    edge_cases_passed = sum(1 for result in edge_case_results.values() if result)
    logger.info(f"Edge Cases: {edge_cases_passed}/{len(edge_case_results)} passed")
    
    error_handling_results = test_results['error_handling']
    error_tests_passed = sum(1 for result in error_handling_results.values() if result)
    logger.info(f"Error Handling: {error_tests_passed}/{len(error_handling_results)} passed")
    
    logger.info(f"Concurrent Interviews: {'PASSED' if test_results['concurrent_interviews'] else 'FAILED'}")
    
    # Overall result
    all_passed = (
        test_results['basic_flow'] and
        edge_cases_passed == len(edge_case_results) and
        error_tests_passed == len(error_handling_results) and
        test_results['concurrent_interviews']
    )
    
    logger.info(f"Overall Test Result: {'PASSED' if all_passed else 'FAILED'}")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(main())