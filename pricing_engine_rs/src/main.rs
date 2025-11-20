use actix_web::{get, post, web, App, HttpResponse, HttpServer, Responder, middleware};
use serde::{Deserialize, Serialize};
use std::env;

mod pricing_logic;

#[derive(Deserialize)]
struct PriceRequest {
    base_price: f64,
    factor: f64,
}

#[derive(Serialize)]
struct PriceResponse {
    final_price: f64,
    processed_by: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    service: String,
    version: String,
}

fn validate_price_request(req: &PriceRequest) -> Result<(), String> {
    if req.base_price < 0.0 {
        return Err("base_price must be non-negative".to_string());
    }
    
    if req.factor < 0.0 {
        return Err("factor must be non-negative".to_string());
    }
    
    if req.base_price > 1_000_000.0 {
        return Err("base_price exceeds maximum allowed value".to_string());
    }
    
    if !req.base_price.is_finite() || !req.factor.is_finite() {
        return Err("Invalid number values".to_string());
    }
    
    Ok(())
}

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(HealthResponse {
        status: "healthy".to_string(),
        service: "pricing_engine".to_string(),
        version: "1.0.0".to_string(),
    })
}

#[post("/calculate")]
async fn calculate(req: web::Json<PriceRequest>) -> impl Responder {
    // Validate input
    if let Err(error_msg) = validate_price_request(&req) {
        return HttpResponse::BadRequest().json(ErrorResponse {
            error: error_msg,
        });
    }
    
    let result = pricing_logic::complex_calculation(req.base_price, req.factor);

    HttpResponse::Ok().json(PriceResponse {
        final_price: result,
        processed_by: "Rust High-Performance Engine v1.0.0".to_string(),
    })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Load port from environment variable or use default
    let port = env::var("RUST_API_PORT")
        .unwrap_or_else(|_| "8080".to_string())
        .parse::<u16>()
        .unwrap_or(8080);
    
    let bind_address = format!("0.0.0.0:{}", port);
    println!("🚀 Pricing Engine (Rust) running on port {}", port);
    
    HttpServer::new(|| {
        App::new()
            .wrap(middleware::Logger::default())
            .service(health)
            .service(calculate)
    })
    .bind(&bind_address)?
    .run()
    .await
}
