### 🛠️ Builder stage
FROM golang:1.22.3-alpine3.20 AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o server ./cmd/api

### 🏃‍♂️ Minimal runtime
FROM alpine:3.20

WORKDIR /app
COPY --from=builder /app/server .

EXPOSE 8080
CMD ["./server"]
