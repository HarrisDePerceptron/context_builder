// Test TypeScript file for context builder

interface User {
    id: number;
    name: string;
    email: string;
}

class UserService {
    private users: User[] = [];

    constructor(protected apiUrl: string) {}

    async getUser(id: number): Promise<User | null> {
        const response = await fetch(`${this.apiUrl}/users/${id}`);
        return response.ok ? await response.json() : null;
    }

    createUser(user: Omit<User, 'id'>): User {
        const newUser: User = {
            id: Date.now(),
            ...user
        };
        this.users.push(newUser);
        return newUser;
    }

    get usersCount(): number {
        return this.users.length;
    }
}

export function formatUserName(user: User): string {
    return `${user.name} (${user.email})`;
}

export const createUserService = (apiUrl: string): UserService => {
    return new UserService(apiUrl);
};

type UserRole = 'admin' | 'user' | 'guest';

export class AdminUserService extends UserService {
    constructor(apiUrl: string, private role: UserRole) {
        super(apiUrl);
    }

    async deleteUser(id: number): Promise<boolean> {
        if (this.role !== 'admin') {
            throw new Error('Insufficient permissions');
        }
        const response = await fetch(`${this.apiUrl}/users/${id}`, {
            method: 'DELETE'
        });
        return response.ok;
    }
} 