// Demo C++ file with intentional bugs for Statbot testing.
// Compile: g++ -o demo demo_code.cpp
// Run:     analyze demo_code.cpp

#include <iostream>
#include <vector>
#include <string>

using namespace std;

// Bug 1 (CPP001): Buffer overflow — writes past array end
void fillArray() {
    int arr[5];
    for (int i = 0; i <= 5; i++) {  // off-by-one: i=5 writes out of bounds!
        arr[i] = i * 10;
    }
}

// Bug 2 (CPP002): Memory leak — early return skips delete
int* createAndProcess(bool hasError) {
    int* data = new int[100];
    
    if (hasError) {
        return nullptr;  // data is leaked here!
    }
    
    for (int i = 0; i < 100; i++) {
        data[i] = i;
    }
    return data;
}

// Bug 3 (CPP003): Use-after-free
void dangerousAccess() {
    int* ptr = new int(42);
    delete ptr;
    cout << "Value: " << *ptr << endl;  // UB: use-after-free!
}

// Bug 4 (CPP004): Null pointer dereference
struct Node {
    int value;
    Node* next;
};

Node* findNode(Node* head, int target) {
    Node* current = head;
    while (current != nullptr) {
        if (current->value == target) return current;
        current = current->next;
    }
    return nullptr;
}

void printFound(Node* head, int target) {
    Node* result = findNode(head, target);
    cout << "Found: " << result->value << endl;  // crash if not found!
}

// Bug 5 (CPP005): Iterator invalidation
void removeNegatives(vector<int>& vec) {
    for (auto it = vec.begin(); it != vec.end(); ++it) {
        if (*it < 0) {
            vec.erase(it);  // invalidates the iterator!
        }
    }
}

// Bug 6 (CPP006): Signed integer overflow in midpoint calc
int binarySearch(int arr[], int size, int target) {
    int low = 0, high = size - 1;
    while (low <= high) {
        int mid = (low + high) / 2;  // UB if low + high overflows!
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}

int main() {
    // Exercise the buggy functions
    fillArray();
    
    int* result = createAndProcess(true);  // leaks memory
    
    dangerousAccess();
    
    Node n1 = {10, nullptr};
    printFound(&n1, 99);  // will crash — node not found
    
    vector<int> nums = {1, -2, 3, -4, 5};
    removeNegatives(nums);
    
    int sorted[] = {1, 2, 3, 4, 5};
    binarySearch(sorted, 5, 3);
    
    return 0;
}
