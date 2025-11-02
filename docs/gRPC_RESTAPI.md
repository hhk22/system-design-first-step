
# gRPC와 REST API 비교

## gRPC

### RPC란?

RPC에서 클라이언트-서버 통신은 클라이언트 API 요청이 로컬 작업이거나 요청이 내부 서버 코드인 것처럼 작동한다. 

```javascript
// REST API 방식. 
const response = await fetch(`https://api.example.com/users/${userId}`, {
    method: "GET",
    headers: ...
})


// gRPC 방식
// gRPC - 서버
const server = new gRPCServer();
server.addFunction('getUser', {id} => {
    return {id: id, name: "홍길동"}
})

server.start("localhost:50051");

// gRPC - 클라이언트
const client = connect('localhost:50051');
const user = await client.getuser(123); // 서버의 함수를 요청하는 방식이 RPC방식!
```

### gRPC 방식은? 

RPC방식은 데이터를 주고받는 방식이 XML/JSON등 여러가지가 있지만, gRPC방식은 protobuf 방식이 있다.  

RPC방식의 프로토콜은 HTTP, TCP등 다양하지만, gRPC방식은 HTTP/2 방식이다. 

RPC는 큰 범주고 gRPC는 구체적인 구현방법이다. 비유하자면,  

RPC = 자동차(개념), gRPC = 테슬라(구체적인 자동차 브랜드) gRPC는 RPC의 최적화된 버전이라고 생각할 수 있다. 

### HTTP/2 방식은?

HTTP/1.1 방식은 요청을 한번에 하나씩만 처리하는 방식이고, HTTP/2 는 여러 요청을 동시에 처리하는 방식이다. 

게다가, 헤더를 압축하고 바이너리 프로토콜로 통신한다. 

## REST API

REST는 소프트웨어 구성 요소간 데이터 교환을 위한 일련의 규칙을 정의하는 소프트웨어 아키텍처 접근 방식. 

HTTP 통신 프로토콜을 기준으로 한다. RESTful API는 POST/GET/PUT/DELETE 방식으로 클라이언트와 서버간의 통신을 한다. 

## 두 방식의 차이 

| 구분         | gRPC            | REST API           |
|:------------|:----------------|:-------------------|
| 통신 방식    | 함수 호출        | HTTP 요청/응답     |
| 데이터 형식  | Protocol Buffers | JSON/XML           |
| 프로토콜     | HTTP/2           | HTTP/1.1, HTTP/2   |
| 성능         | 빠름             | 보통               |
| 타입 안전성  | 강타입           | 약타입              |
| 브라우저 지원| 제한적           | 완전 지원           |
| 스트리밍     | 지원             | 제한적              |
| 코드 생성    | 자동             | 수동               |
| 에러 처리    | 자동             | 수동               |
| 학습 곡선    | 높음             | 낮음               |


REST API를 사용할 때는 소프트웨어 구성 요소 간에 전달되는 데이터 구조가 일반적으로 JSON 데이터 교환 형식으로 표현됩니다. XML 및 HTML과 같은 다른 데이터 형식을 전달하는 것도 가능합니다. JSON은 읽기 쉽고 유연하지만 직렬화해야 하고 프로그래밍 언어로 번역해야 합니다.

반대로 gRPC는 기본적으로 Protocol Buffer(Protobuf) 형식을 사용하지만 기본 JSON 지원도 제공합니다. 서버는 프로토타입 사양 파일에서 Protocol Buffer 인터페이스 설명 언어(IDL)를 사용하여 데이터 구조를 정의합니다. gRPC는 구조를 바이너리 형식으로 직렬화한 다음 지정된 프로그래밍 언어로 역직렬화합니다. 이 메커니즘은 전송 중에 압축되지 않는 JSON을 사용하는 것보다 더 빠릅니다. Protocol Buffer는 JSON과 함께 사용되는 REST API와 달리 사람이 읽을 수 없습니다.

