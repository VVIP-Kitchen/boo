### 🛠️ Builder stage
FROM golang:1.22.3-alpine3.20 AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o server ./cmd/api

### 🏃‍♂️ Minimal runtime
FROM gcr.io/distroless/static-debian12

WORKDIR /app
COPY --from=builder /app/server .

EXPOSE 8080
CMD ["./server"]
