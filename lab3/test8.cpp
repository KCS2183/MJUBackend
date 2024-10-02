#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <string.h>
#include <unistd.h>

#include <iostream>
#include <string>

using namespace std;

int main()
{
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0)
        return 1;

    char buf[65536];

    struct sockaddr_in sin;
    memset(&sin, 0, sizeof(sin));
    sin.sin_family = AF_INET;
    sin.sin_addr.s_addr = inet_addr("127.0.0.1");
    sin.sin_port = htons(10000 + 207);
    if (bind(s, (struct sockaddr *)&sin, sizeof(sin)) < 0)
    {
        cerr << strerror(errno) << endl;
        return 0;
    }

    while (true)
    {
        memset(&sin, 0, sizeof(sin));
        socklen_t sin_size = sizeof(sin);
        int numBytes = recvfrom(s, buf, sizeof(buf), 0, (struct sockaddr *)&sin, &sin_size);
        if (numBytes > 0)
        {
            buf[numBytes] = '\0';
            cout << "Server Recevied: " << buf << endl;

            numBytes = sendto(s, buf, numBytes, 0, (struct sockaddr *)&sin, sizeof(sin));
            cout << "Server Sent: " << numBytes << endl;
        }
    }

    close(s);
    return 0;
}