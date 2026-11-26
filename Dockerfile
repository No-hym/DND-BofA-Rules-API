# Build both the HTTP service and the data management CLI.
FROM golang:1.27.4-alpine AS build
WORKDIR /src
RUN apk add --no-cache ca-certificates git
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/rules-api ./cmd/rules-api \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/rules ./cmd/rules \
 && CGO_ENABLED=0 go install github.com/pressly/goose/v3/cmd/goose@v3.30.2

FROM alpine:3.23
RUN apk add --no-cache ca-certificates tzdata \
 && addgroup -S rules && adduser -S -G rules rules
WORKDIR /app
COPY --from=build /out/rules-api /app/rules-api
COPY --from=build /out/rules /app/rules
COPY --from=build /go/bin/goose /usr/local/bin/goose
COPY db/migrations /app/db/migrations
COPY data /app/data
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod 0555 /app/entrypoint.sh && chown -R rules:rules /app
USER rules
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/rules-api"]
